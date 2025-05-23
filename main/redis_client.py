from django.conf import settings

import redis


pool = redis.ConnectionPool(
    decode_responses=True,  # This makes Redis return strings instead of bytes
    max_connections=settings.DRIVERS_COUNT+5,  # 💡‌ قانون سرانگشتی: تعداد اتصال‌های همزمان = تعداد تردها + 10٪ بافر
    host='localhost',
    port=6379
)

REDIS = redis.Redis(connection_pool=pool)
