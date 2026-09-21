import os
import redis.asyncio as redis_lib

REDIS_DETECTION_URL = os.environ.get("REDIS_DETECTION_URL", "redis://redis-detection-cache:6379")

async def init_redis() -> redis_lib.Redis:
    return await redis_lib.from_url(
        REDIS_DETECTION_URL,
        encoding="utf-8",
        decode_responses=True
    )

async def close_redis(redis_instance: redis_lib.Redis):
    if redis_instance:
        await redis_instance.close()
