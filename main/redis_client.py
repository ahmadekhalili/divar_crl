from django.conf import settings

from pathlib import Path
import os
import environ
import redis

env = environ.Env()
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent.parent, '.env'))


pool = redis.ConnectionPool(
    decode_responses=True,  # This makes Redis return strings instead of bytes
    max_connections=settings.DRIVERS_COUNT+5,  # 💡‌ قانون سرانگشتی: تعداد اتصال‌های همزمان = تعداد تردها + 10٪ بافر
    host=env('REDIS_HOST'),
    port=6379
)

REDIS = redis.Redis(connection_pool=pool)
