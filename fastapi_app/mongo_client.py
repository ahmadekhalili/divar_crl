from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
from pathlib import Path
import environ
import asyncio
import os
import logging


BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))


# ─── MongoDB setup ─────────────────────────────────────────────────────────────
client = AsyncIOMotorClient(f"mongodb://{env('MONGO_HOST')}:27017")
db = client[f"{env('MONGO_DBNAME')}"]

client_sync = MongoClient("mongodb://{env('MONGO_HOST')}:27017")
db_sync = client_sync[f"{env('MONGO_DBNAME')}"]
