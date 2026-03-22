"""Global Redis client instance."""

from typing import Optional
from api.services.redis_service import RedisService

redis_client: Optional[RedisService] = None


def init_redis() -> RedisService:
    global redis_client
    redis_client = RedisService()
    return redis_client


def get_redis() -> RedisService:
    if redis_client is None:
        return init_redis()
    return redis_client
