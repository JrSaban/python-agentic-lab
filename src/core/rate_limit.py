"""Rate limit utilities."""

from typing import cast

from redis.asyncio import Redis


async def seconds_until_reset(redis_client: Redis, key: str) -> int:
    """Remaining TTL of a rate limit counter, in seconds, for the Retry-After header.

    Never less than 1: a counter without TTL (-1) or already gone (-2) still means
    the client should wait before retrying, not retry immediately.
    """
    ttl = await redis_client.ttl(key)
    return max(ttl, 1)


async def get_retry_after(redis_client: Redis, keys: list[str], max_attempts: int) -> int | None:
    """Seconds to wait if any of the given keys has reached the limit, else None."""
    for key in keys:
        attempts = cast(str | None, await redis_client.get(key))
        if attempts is not None and int(attempts) >= max_attempts:
            return await seconds_until_reset(redis_client, key)
    return None


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
