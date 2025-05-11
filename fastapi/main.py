# write to mongo (our files) asynchron
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, AnyHttpUrl, Field, validator
from typing import List, Dict, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ReturnDocument
from pathlib import Path
from bson import ObjectId
import environ
import asyncio
import os
import logging

from methods import upload_and_get_image_paths, logger, consume_data

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))
app = FastAPI()

# ─── MongoDB setup ─────────────────────────────────────────────────────────────
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client[f"{env('MONGO_DBNAME')}"]


# ─── Pydantic model reflecting your FileMongoSerializer ────────────────────────
class FileItem(BaseModel):
    file_uid: str   # required, id created for each file by divar
    phone: Optional[int] = Field(None, description="Phone number, None if unavailable")
    title: str = Field(..., max_length=255, description="Listing title")
    metraj: Optional[str] = Field("", max_length=50)
    age: Optional[str] = Field("", max_length=50)
    otagh: Optional[str] = Field("", max_length=50)
    total_price: Optional[str] = Field("", max_length=100)
    price_per_meter: Optional[str] = Field("", max_length=100)
    floor_number: Optional[str] = Field("", max_length=50)
    general_features: List[str] = []
    features: List[str] = []
    image_srcs: List[str] = []
    image_paths: List[str] = []
    map_paths: List[str] = []
    specs: Dict[str, str] = {}
    description: Optional[str] = ""
    url: str

    @validator("phone")
    def phone_must_be_positive(cls, v):
        if v is not None and v < 0:
            raise ValueError("Phone number must be positive")
        return v

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




@app.on_event("startup")
async def start_consumer():  # runs in startup to always runs (keep listening to redis)
    asyncio.create_task(consume_data())



# ─── severa file creation endpoint ──────────────────────────────────────────────────────
@app.post("/files_create", response_model=List[FileItem])
async def create_files(items: List[FileItem]):
    logger.info("post requested sended successfully to fastapi: create_files")
    try:
        await db.client.server_info()
    except Exception as e:
        logger.error(f"Could not connect to MongoDB. error: {e}")
        raise

    try:
        docs = []
        for item in items:
            dic_value = item.dict()
            if dic_value.get("image_srcs"):
                dic_value["image_paths"] = await upload_and_get_image_paths(dic_value["image_srcs"], dic_value["file_uid"])
            docs.append(dic_value)
    except Exception as e:
        logger.error(f"Could not upload file images: {e}")

    try:
        # insert many
        result = await db.file.insert_many(docs)
        # attach each new ObjectId
        for doc, oid in zip(docs, result.inserted_ids):
            doc["_id"] = str(oid)
        return docs
    except Exception as e:
        logger.error(f"Could not insert files in mongo db. error: {e}")



@app.get("/test", tags=["health"])
async def health_check():
    print("1111111111111111")
    logger.info("^^^^^^^^^^^^^^^")
    return {"status": "up", "version": app.version}
