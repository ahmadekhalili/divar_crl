from fastapi import FastAPI, HTTPException
from typing import List, Dict, Optional
from bson import ObjectId
from pathlib import Path
import environ
import asyncio
import os

import logging
from log_handler import init_logging
init_logging()    # should import before critical local imports. now can use logging.ge..

from methods import upload_and_get_image_paths, listen_redis
from mongo_client import db
from models import ApartmentItem

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))
app = FastAPI()

logger = logging.getLogger('fastapi')


@app.on_event("startup")
async def start_consumer():  # runs in startup to always runs (keep listening to redis)
    await db.apartment.create_index("uid", unique=False)
    await db.zamin_kolangy.create_index("uid", unique=False)
    await db.vila.create_index("uid", unique=False)  # non‐unique index
    asyncio.create_task(listen_redis())


# ─── serve file creation endpoint ──────────────────────────────────────────────────────
@app.post("/files_create")
async def write_to_mongo(items: list):
    logger.info("post request sent successfully to fastapi: create_files")
    try:        # check mongo connection first
        await db.client.server_info()
    except Exception as e:
        logger.error(f"Could not connect to MongoDB. error: {e}")
        raise

    try:         # upload file images eficiently (asynchron)
        docs = []
        for item in items:
            dic_value = item.dict()
            if dic_value.get("image_srcs"):
                dic_value["image_paths"] = await upload_and_get_image_paths(dic_value["image_srcs"], dic_value["uid"])
            docs.append(dic_value)
    except Exception as e:
        logger.error(f"Could not upload file images: {e}")

    try:  # write to mongo
        # insert many
        result = await db.file.insert_many(docs)
        logger.info(f"successfully was written files to mongo")
        # attach each new ObjectId
        for doc, oid in zip(docs, result.inserted_ids):
            doc["_id"] = str(oid)

        return docs
    except Exception as e:
        logger.error(f"Could not insert files in mongo db. error: {e}")


@app.get("/test", tags=["health"])
async def health_check():
    print("test fastapi function called")
    logger.info("test fastapi function called, logger")
    return {"status": "up", "version": app.version}
