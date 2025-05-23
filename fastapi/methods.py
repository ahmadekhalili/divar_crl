import logging
from log_handler import init_logging
init_logging()    # should import before critical local imports. now can use logging.ge..

from fastapi import HTTPException
from httpx import AsyncClient, Limits, HTTPError
from typing import List, Dict
from pathlib import Path
import redis.asyncio as redis
from pymongo import ReturnDocument
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.exceptions import ResponseError as RedisResponseError
from typing import Any
import aiofiles
import urllib.parse
import environ
import os
import sys
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import django
from django.conf import settings

from mongo_client import db
from models import ApartmentItem

# Step 1: Add project root (C:\backs\divar_crl) to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent  # Move one level up from fastapi/
sys.path.append(str(BASE_DIR))  # from you can imports from django root, from divar_crl import settings  # ✅ Works because divar_crl/ is now on sys.path
from divar_crl.settings import DEBUG

env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))

r = redis.Redis()

card_logger = logging.getLogger('cards')
logger = logging.getLogger('fastapi')


class FileCrawl:
    def __init__(self, uid, url, **extras):
        self.uid = uid
        self.url = url
        self.file_errors = []
        self.file_warns = []
        for key, value in extras.items():   # set auto additional attrs of the FileCrawl (file_errors, file_warns..)
            setattr(self, key, value)

async def upload(client: AsyncClient,
                 url: str,
                 uid: str) -> str:
    """
    Download `url` with `client`, save into `dest_folder`,
    and return the full URL to access it.
    """

    rel = Path(env('SCREENSHOT_IMAGE_PATH').format(uid=uid))  # it must Path obj
    dest_folder = BASE_DIR / rel
    # 1) Make the request (streaming supported but for simplicity we load all at once)
    try:
        resp = await client.get(url, timeout=10.0)
        resp.raise_for_status()
    except HTTPError:
        raise

    # 2) Strip query, sanitize filename
    parsed = urllib.parse.urlparse(url)
    filename = Path(parsed.path).name or "unnamed"
    # Prevent funny business:
    filename = filename.replace("..", "_")

    # 3) Ensure folder exists
    dest_folder.mkdir(parents=True, exist_ok=True)

    # 4) Write file asynchronously
    file_path = dest_folder / filename

    # 1) Make the request as a stream
    async with client.stream("GET", url, timeout=10.0) as resp:
        resp.raise_for_status()
        async with aiofiles.open(file_path, "wb") as f:  # Write file asynchronously in chunks (prevent high payload in memory)
            async for chunk in resp.aiter_bytes():
                await f.write(chunk)

    return str(file_path)   # e.g. "media/file_images/file 3"


async def upload_and_get_image_paths(
    urls: List[str],
    uid: str,
):
    """
    Download each image URL and save it under:
      MEDIA_ROOT/file_images/file_<file_number>/<original_filename>
    Returns a list of **full** URLs pointing at each saved image.
    """

    limits = Limits(max_connections=10, max_keepalive_connections=5)
    async with AsyncClient(limits=limits) as client:
        tasks = []
        for url in urls:
            tasks.append(upload(client, url, uid))

        # gather will raise on the first exception by default:
        uploaded_paths = []
        for coro in tasks:
            try:
                path = await coro
                uploaded_paths.append(path)
            except HTTPError:
                # skip failed downloads
                continue

    if not uploaded_paths:
        raise HTTPException(status_code=400, detail="No images could be downloaded.")

    return uploaded_paths


async def save_to_mongodb(data: Dict[str, Any], filecrawl):  # dont sames multiple instance just for log readable (card_logger.info(message_to_write))
    """
    Validate incoming `data` dict against ApartmentItem, generate a unique uid
    if not present, and upsert into MongoDB.
    """
    logger.info(f"save_to_mongodb just started. {filecrawl}")
    try:
        try:
            await db.client.server_info()
        except Exception as e:
            message = f"Could not connect to MongoDB. error: {e}"
            logger.error(message)
            filecrawl.file_errors.append(message)

        if data.get("image_srcs"):  # upload to the hard and set image_paths
            data["image_paths"] = await upload_and_get_image_paths(data["image_srcs"], data["uid"])

        now = datetime.now(ZoneInfo("UTC"))   # mongo default saves in UTC in any way!
        data["created_at"] = now

        logger.debug("Starting save_to_mongodb for redis_record: %r", data)
        # 2. Validate & normalize with Pydantic
        item = ApartmentItem(**data)
        logger.info("Validated ApartmentItem; uid=%s, name=%s", item.uid, getattr(item, "title", "<no title>"))

        # 3. Prepare the document for MongoDB
        doc = item.dict()
        # Optionally, you can use uid as the MongoDB _id:
        # doc["_id"] = item.uid

        # 4. Upsert into `file` collection
        if data['category'] == "apartment":  # item has not category key
            result = await db.apartment.insert_one(doc)
        elif data['category'] == "zamin_kolangy":
            result = await db.zamin_kolangy.insert_one(doc)
        elif data['category'] == "vila":
            result = await db.vila.insert_one(doc)
        logger.info("Inserted new document in mongo db with _id=%s", result.inserted_id)
        uid, url = getattr(filecrawl, 'uid', None), getattr(filecrawl, 'url', None)
        file_errors, file_warns = getattr(filecrawl, 'file_errors', None), getattr(filecrawl, 'file_warns', None)
        symbol = "✅" if not file_errors else "❌"
        if symbol == "✅":
            if file_warns:
                symbol = "✅⚠️"
        message_to_write = f"{symbol} - (uid={uid}, url={url})  errors: {file_errors}  warns: {file_warns}"
        card_logger.info(message_to_write)
    except Exception as e:
        message = f"Failed to save {data.get('category')} to MongoDB. totaly skaped save_to_mongodb func. error: {e}"
        logger.error(message)


async def listen_redis():   # always listens to redis and if a record added read and write to mongo
    stream = 'data_stream'
    group = 'fastapi_group'
    consumer_name = 'fastapi_1'
    error_counts, max_retry = 0, 10  # this prevent from infinit prints of log when delete stream redis for refresh
    try:
        await r.xgroup_create(stream, group, mkstream=True)
    except RedisResponseError as e:
        if "BUSYGROUP" not in str(e):       # BUSYGROUP means group already exists
            logger.error(f"Could not create or verify Redis group. e: {e}")
            raise

    while True:
        try:
            # 5 ثانیه منتظر بمون تا پیام جدید بیاد. اگه نبود دوباره بچرخ
            messages = await r.xreadgroup(group, consumer_name, {stream: '>'}, count=10, block=5000)
            if not messages:
                continue
            if messages:
                error_counts = 0      # reset on success
            logger.debug("Received %d message batch", sum(len(entries) for _, entries in messages))
            for _, entries in messages:
                for msg_id, entry in entries:
                    try:
                        filecrawl = None   # prevent reference error
                        data = json.loads(entry[b'data'])  # data is exact type was written to redis. if was list is list, if was dic is dict. it is now dict because in django crawl.add_finall_card_to_redis we set dict
                        file_crawl_extra = json.loads(entry[b'file_crawl_extra'])

                        logger.debug("Processing message %s: %r", msg_id, data)
                        filecrawl = FileCrawl(uid=data['uid'], url=data['url'], **file_crawl_extra)  # auto set attrs
                        await save_to_mongodb(data, filecrawl)
                        await r.xack(stream, group, msg_id)  # sign as proceed message
                        if DEBUG == False:
                            await r.xdel(stream, group, msg_id)  # dont fill ram with thousands of records
                        logger.info("Acknowledged redis message %s", msg_id)
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON in response. entry id: {msg_id}; skipping; error: {e}", )
                        if filecrawl:
                            filecrawl.file_errors.append("Invalid JSON in response.")
                    except Exception as e:
                        logger.error(f"Error handling message {msg_id}; skipping; errpr: {e}", )
                        if filecrawl:
                            filecrawl.file_errors.append("error taking record from redis")

        except Exception as e:
            if error_counts < max_retry:  # else dont fill logs and just wait until stream creates (just restart fastapi)
                logger.error(f"Error reading from Redis stream; retrying loop. error: {e}.")
            if error_counts == 10:
                logger.error("Max retries exided. restart fastapi.")
            max_retry += 1
            # small sleep could be added here in production to avoid a tight error loop


# ─── Helper to get an auto-incrementing counter ────────────────────────────────
async def get_file_number(name: str) -> int:
    """Atomically increment and return a counter from 'counters' collection."""
    doc = await db.counters.find_one_and_update(
        {"_id": name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER
    )
    return doc["seq"]
