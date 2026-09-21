import os
import json
from typing import Optional, List
import redis.asyncio as redis_lib
from fastapi import Request

# TTL (defaults to 24 hours)
REDIS_EXPIRE_SECONDS: int = int(os.getenv("REDIS_EXPIRE_SECONDS", str(24 * 60 * 60)))
# Fallback URL if app.state.redis is not provided by your app startup
REDIS_DETECTION_URL = os.environ.get("REDIS_DETECTION_URL", "redis://redis-detection-cache:6379")


def get_redis_key(account_id: str, service: str) -> str:
    """Canonical cache key for allowed data elements."""
    return f"allowed_data_elements:{account_id}:{service}"


async def get_or_create_redis(request: Request) -> redis_lib.Redis:
    """
    Prefer an existing connection at request.app.state.redis.
    If missing, lazily create one from DEFAULT_REDIS_URL and store it.
    """
    existing = getattr(request.app.state, "redis", None)
    if existing is not None:
        return existing
    redis = redis_lib.from_url(REDIS_DETECTION_URL , decode_responses=False)
    request.app.state.redis = redis
    return redis


async def prime_allowed_elements_cache(
    redis: redis_lib.Redis,
    account_id: str,
    service: str,
    data_elements: Optional[List[str]],
) -> None:
    """
    Upsert the allowed data elements into Redis immediately with expiry.
    Accepts None and stores an empty list to avoid stale reads.
    """
    key = get_redis_key(account_id, service)
    payload = json.dumps(data_elements or [])
    await redis.set(key, payload, ex=REDIS_EXPIRE_SECONDS)
