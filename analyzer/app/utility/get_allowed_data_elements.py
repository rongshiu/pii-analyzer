# app/utility/get_allowed_data_elements.py
import json
import os
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.utility.logger import get_logger
import redis.asyncio as redis_lib
from fastapi import HTTPException

logger = get_logger()

REDIS_EXPIRE_SECONDS = 24 * 60 * 60  # 24 hours


def get_redis_key(account_id: str, service: str) -> str:
    return f"allowed_data_elements:{account_id}:{service}"


async def get_allowed_data_elements_redis_first(
    db: AsyncSession, redis: redis_lib.Redis, account_id: str, service: str
) -> list[str]:
    redis_key = get_redis_key(account_id, service)

    # Try Redis first
    logger.info(f"Checking Redis cache for key: {redis_key}")
    cached = await redis.get(redis_key)
    if cached:
        try:
            logger.info(f"Cache hit for key: {redis_key}")
            return json.loads(cached)
        except Exception as e:
            logger.warning(f"Failed to decode cached data for key {redis_key}: {str(e)}")

    logger.info(f"Cache miss. Querying Postgres for account_id={account_id}, service={service}")
    # Fallback to Postgres (raw SQL version)
    query = text("""
        SELECT data_elements 
        FROM pii_scanner.detection_specifications
        WHERE account_id = :account_id AND service = :service
    """)
    result = await db.execute(query, {
        "account_id": account_id,
        "service": service
    })
    row = result.fetchone()

    if not row:
        # Raise 404 when no record found
        detail = f"No detection_specifications found for account_id={account_id}, service={service}"
        logger.warning(detail)
        raise HTTPException(status_code=404, detail=detail)

    allowed = row[0] if row else []

    logger.info(f"Fetched from Postgres: {allowed}")

    # Cache in Redis with a 24-hour expiration
    try:
        await redis.set(redis_key, json.dumps(allowed), ex=REDIS_EXPIRE_SECONDS)
        logger.info(f"Cached result in Redis for key: {redis_key} (TTL={REDIS_EXPIRE_SECONDS}s)")
    except Exception as e:
        logger.warning(f"Failed to cache result in Redis for key {redis_key}: {str(e)}")

    return allowed
