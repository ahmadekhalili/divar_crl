from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path
import environ
import asyncio
import os
import logging


BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
env.read_env(os.path.join(BASE_DIR, '.env'))


# ─── MongoDB setup ─────────────────────────────────────────────────────────────
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client[f"{env('MONGO_DBNAME')}"]
