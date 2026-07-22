"""
Shared Redis connection pool.
Initialized by app.main lifespan; imported by deps.py to avoid circular imports.
"""

from redis.asyncio import Redis
from app.core.config import get_settings

_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    """Return the shared Redis client. Must be called after init_redis()."""
    if _redis_client is None:
        raise RuntimeError(
            "Redis client has not been initialized. Call init_redis() first."
        )
    return _redis_client


def init_redis() -> Redis:
    """Create the Redis connection pool and store it as the module singleton."""
    global _redis_client
    settings = get_settings()
    _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client  # type: ignore[return-value]


async def close_redis() -> None:
    """Close the Redis connection pool on shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
