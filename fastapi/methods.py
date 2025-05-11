from fastapi import HTTPException
from httpx import AsyncClient, Limits, HTTPError
from typing import List
from pathlib import Path
import redis.asyncio as redis
from logging.handlers import RotatingFileHandler
import logging
import aiofiles
import urllib.parse
import environ
import os
import json

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))


# 1) Create a rotating file handler in the current directory
handler = RotatingFileHandler(
    "app.log",
    maxBytes=5*1024*1024,  # 5 MB per file
    backupCount=2          # keep two old log files around
)
# 2) Choose a log format
formatter = logging.Formatter(
    "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
)
handler.setFormatter(formatter)

logger = logging.getLogger("fastapi")
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

r = redis.Redis()


async def consume_data():   # always listens to redis and if a record added read and write to mongo
    stream = 'data_stream'
    group = 'fastapi_group'
    consumer_name = 'consumer_1'
    await r.xgroup_create(stream, group, mkstream=True)

    while True:
        messages = await r.xreadgroup(group, consumer_name, {stream: '>'}, count=10, block=5000)
        if messages:
            for _, entries in messages:
                for id, entry in entries:
                    data = json.loads(entry[b'data'])
                    await save_to_mongodb(data)
                    await r.xack(stream, group, id)


async def upload(
    client: AsyncClient,
    url: str,
    file_uid: str,
) -> str:
    """
    Download `url` with `client`, save into `dest_folder`,
    and return the full URL to access it.
    """
    dest_folder = env('screenshot_image_path').format(uid=file_uid)
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
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(resp.content)

    return f"{file_path}"   # e.g. "media/file_images/file 3"


async def upload_and_get_image_paths(
    urls: List[str],
    file_uid: str,
):
    """
    Download each image URL and save it under:
      MEDIA_ROOT/file_images/file_<file_number>/<original_filename>
    Returns a list of **full** URLs pointing at each saved image.
    """

    limits = Limits(max_connections=10, max_keepalive=5)
    async with AsyncClient(limits=limits) as client:
        tasks = []
        for url in urls:
            tasks.append(upload(client, url, file_uid))

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


