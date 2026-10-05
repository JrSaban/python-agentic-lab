"""Rate limit utilities."""

from typing import cast

from redis.asyncio import Redis


async def is_rate_limited(redis_client: Redis, keys: list[str], max_attempts: int) -> bool:
    """Check if the rate limit has been reached for any of the given keys."""
    for key in keys:
        attempts = cast(str | None, await redis_client.get(key))
        if attempts is not None and int(attempts) >= max_attempts:
            return True
    return False


async def increment_rate_limit(
    redis_client: Redis, keys: list[str], window_minutes: int
) -> dict[str, int]:
    """Increment the rate limit for the given keys."""
    all_attempts = {}

    for key in keys:
        attempts = await redis_client.incr(key)
        await redis_client.expire(key, 60 * window_minutes, nx=True)
        all_attempts[key] = attempts

    return all_attempts
