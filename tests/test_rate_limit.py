"""Tests d'intégration du middleware de rate limiting général."""

import fakeredis
from httpx import AsyncClient

from src.core.config import settings
from src.core.security import create_access_token

IP_KEY = "rate_limit:general:ip:127.0.0.1"


async def test_request_under_the_limit_passes(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """The request that brings the counter exactly to GENERAL_RATE_LIMIT_MAX_REQUESTS
    still passes — the limit is inclusive."""
    await redis_client.set(IP_KEY, str(settings.GENERAL_RATE_LIMIT_MAX_REQUESTS - 1))

    response = await client.get("/health")
    assert response.status_code == 200


async def test_request_over_the_limit_returns_429(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """Once GENERAL_RATE_LIMIT_MAX_REQUESTS requests have been made, the next one → 429."""
    await redis_client.set(IP_KEY, str(settings.GENERAL_RATE_LIMIT_MAX_REQUESTS))

    response = await client.get("/health")
    assert response.status_code == 429


async def test_blocked_request_still_carries_request_id(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """The rate limit middleware sits inside log_requests, so a 429 short-circuit
    still goes through it and gets an X-Request-ID."""
    await redis_client.set(IP_KEY, str(settings.GENERAL_RATE_LIMIT_MAX_REQUESTS))

    response = await client.get("/health")
    assert response.status_code == 429
    assert "X-Request-ID" in response.headers


async def test_first_request_sets_the_window_ttl(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """The first request of a window creates the counter with a TTL of
    GENERAL_RATE_LIMIT_WINDOW_MINUTES."""
    await client.get("/health")

    assert await redis_client.get(IP_KEY) == "1"
    ttl = await redis_client.ttl(IP_KEY)
    assert 0 < ttl <= 60 * settings.GENERAL_RATE_LIMIT_WINDOW_MINUTES


async def test_valid_token_is_counted_per_user(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """A valid access token is counted under the user's id, not the IP."""
    token = create_access_token({"sub": "42"})

    await client.get("/health", headers={"Authorization": f"Bearer {token}"})

    assert await redis_client.get("rate_limit:general:user:42") == "1"
    assert await redis_client.get(IP_KEY) is None


async def test_exhausted_user_does_not_block_same_ip(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """A user who exhausted their own counter doesn't block anonymous requests
    coming from the same IP — the two counters are independent."""
    await redis_client.set(
        "rate_limit:general:user:42", str(settings.GENERAL_RATE_LIMIT_MAX_REQUESTS)
    )
    token = create_access_token({"sub": "42"})

    blocked = await client.get("/health", headers={"Authorization": f"Bearer {token}"})
    assert blocked.status_code == 429

    anonymous = await client.get("/health")
    assert anonymous.status_code == 200


async def test_invalid_token_falls_back_to_ip(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """An invalid or expired token never makes the middleware fail: the request
    is counted under the IP and goes on."""
    response = await client.get("/health", headers={"Authorization": "Bearer not-a-jwt"})

    assert response.status_code == 200
    assert await redis_client.get(IP_KEY) == "1"


async def test_non_bearer_header_falls_back_to_ip(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """An Authorization header with another scheme is ignored: counted under the IP."""
    response = await client.get("/health", headers={"Authorization": "Basic dXNlcjpwYXNz"})

    assert response.status_code == 200
    assert await redis_client.get(IP_KEY) == "1"
