import redis


REDIS = redis.Redis(decode_responses=True)  # This makes Redis return strings instead of bytes
