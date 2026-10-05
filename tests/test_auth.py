"""Tests d'intégration de l'endpoint Auth."""

import fakeredis
from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.modules.users.repository import UserRepository


async def register_user(client: AsyncClient, email: str = "test@gmail.com") -> Response:
    return await client.post(
        "/api/v1/users",
        json={
            "email": email,
            "first_name": "John",
            "last_name": "Doe",
            "pseudo": "JohnDoe",
            "password": "password",
            "confirm_password": "password",
        },
    )


async def test_login_success(client: AsyncClient) -> None:
    """Correct email + password (POST /api/v1/login) → 200, access_token present."""
    response = await register_user(client)
    assert response.status_code == 201
    response = await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "password"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    """Correct email but wrong password → 401."""
    response = await register_user(client)
    assert response.status_code == 201
    response = await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "wrong_password"}
    )
    assert response.status_code == 401


async def test_login_unknown_email_returns_401(client: AsyncClient) -> None:
    """Email that was never registered → 401."""
    response = await register_user(client)
    assert response.status_code == 201
    response = await client.post(
        "/api/v1/login", json={"email": "unknown@gmail.com", "password": "password"}
    )
    assert response.status_code == 401


async def test_login_inactive_account_returns_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Correct credentials, but the account has been deactivated → 401."""
    response = await register_user(client)
    assert response.status_code == 201
    user_id = response.json()["id"]

    user_repo = UserRepository(db_session)
    user = await user_repo.get_by_id(user_id)

    assert user is not None
    await user_repo.set_active(user, False)
    response = await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "password"}
    )
    assert response.status_code == 401


async def test_login_rate_limit_blocks_after_max_attempts(client: AsyncClient) -> None:
    """Wrong password repeated up to LOGIN_RATE_LIMIT_MAX_ATTEMPTS times still returns 401;
    the next attempt is blocked with 429."""
    await register_user(client)

    for _ in range(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS):
        response = await client.post(
            "/api/v1/login", json={"email": "test@gmail.com", "password": "wrong_password"}
        )
        assert response.status_code == 401

    response = await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "wrong_password"}
    )
    assert response.status_code == 429
    window_seconds = 60 * settings.LOGIN_RATE_LIMIT_WINDOW_MINUTES
    assert 0 < int(response.headers["Retry-After"]) <= window_seconds


async def test_login_retry_after_is_the_longest_blocking_wait(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """When both the IP and the email counters are blocking, Retry-After is the longer
    of the two TTLs: retrying after the shorter one would still be blocked."""
    blocked = str(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS)
    await redis_client.set("rate_limit:login:ip:127.0.0.1", blocked, ex=300)
    await redis_client.set("rate_limit:login:email:test@gmail.com", blocked, ex=1500)

    response = await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "wrong_password"}
    )
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 300


async def test_login_success_never_counts_toward_rate_limit(client: AsyncClient) -> None:
    """Successful logins never increment the rate limit counters, no matter how many
    in a row."""
    await register_user(client)

    for _ in range(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS + 2):
        response = await client.post(
            "/api/v1/login", json={"email": "test@gmail.com", "password": "password"}
        )
        assert response.status_code == 200


async def test_login_rate_limit_not_reset_by_a_successful_login(client: AsyncClient) -> None:
    """A successful login in between failures does not reset the failure counter:
    failures keep accumulating across it."""
    await register_user(client)

    async def fail() -> Response:
        return await client.post(
            "/api/v1/login", json={"email": "test@gmail.com", "password": "wrong_password"}
        )

    assert (await fail()).status_code == 401
    assert (await fail()).status_code == 401

    success = await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "password"}
    )
    assert success.status_code == 200

    assert (await fail()).status_code == 401
    assert (await fail()).status_code == 401
    assert (await fail()).status_code == 401  # 5th failure overall

    assert (await fail()).status_code == 429


async def test_login_rate_limit_blocked_by_ip_with_a_fresh_email(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """The IP counter alone, already at the threshold, is enough to block — even for
    an email that has never failed before."""
    await register_user(client)
    await redis_client.set(
        "rate_limit:login:ip:127.0.0.1", str(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS)
    )

    response = await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "password"}
    )
    assert response.status_code == 429


async def test_login_rate_limit_blocked_by_email_with_a_fresh_ip(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """The email counter alone, already at the threshold, is enough to block — even
    though the IP counter is untouched."""
    await register_user(client)
    await redis_client.set(
        "rate_limit:login:email:test@gmail.com", str(settings.LOGIN_RATE_LIMIT_MAX_ATTEMPTS)
    )

    response = await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "password"}
    )
    assert response.status_code == 429


async def test_login_rate_limit_window_is_fixed_not_sliding(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """The TTL is set on the first failed attempt and never pushed back by later ones
    within the same window — a fixed window, not a sliding one."""
    await register_user(client)

    await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "wrong_password"}
    )
    first_ttl = await redis_client.ttl("rate_limit:login:email:test@gmail.com")
    assert first_ttl > 0

    await client.post(
        "/api/v1/login", json={"email": "test@gmail.com", "password": "wrong_password"}
    )
    second_ttl = await redis_client.ttl("rate_limit:login:email:test@gmail.com")
    assert second_ttl <= first_ttl


async def test_refresh_success(client: AsyncClient) -> None:
    """A valid refresh token (POST /api/v1/refresh) → 200, a new access_token."""
    user_response = await register_user(client)
    user_email = user_response.json()["email"]
    user_password = "password"

    logged_in_response = await client.post(
        "/api/v1/login", json={"email": user_email, "password": user_password}
    )
    refresh_token = logged_in_response.json()["refresh_token"]

    response = await client.post("/api/v1/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_refresh_invalid_token_returns_401(client: AsyncClient) -> None:
    """A refresh token that was never issued (or already expired/revoked) → 401."""
    response = await client.post("/api/v1/refresh", json={"refresh_token": "invalid_token"})
    assert response.status_code == 401


async def test_refresh_rotates_the_refresh_token(client: AsyncClient) -> None:
    """A successful /refresh returns a *different* refresh_token from the one sent,
    and the old one no longer works — rotation, not reuse."""
    user_response = await register_user(client)
    user_email = user_response.json()["email"]

    logged_in_response = await client.post(
        "/api/v1/login", json={"email": user_email, "password": "password"}
    )
    old_refresh_token = logged_in_response.json()["refresh_token"]

    refresh_response = await client.post(
        "/api/v1/refresh", json={"refresh_token": old_refresh_token}
    )
    assert refresh_response.status_code == 200
    new_refresh_token = refresh_response.json()["refresh_token"]
    assert new_refresh_token != old_refresh_token

    reuse_response = await client.post("/api/v1/refresh", json={"refresh_token": old_refresh_token})
    assert reuse_response.status_code == 401


async def test_refresh_with_rotated_token_still_works(client: AsyncClient) -> None:
    """The newly rotated refresh_token is itself usable for a subsequent refresh."""
    user_response = await register_user(client)
    user_email = user_response.json()["email"]

    logged_in_response = await client.post(
        "/api/v1/login", json={"email": user_email, "password": "password"}
    )
    first_refresh_token = logged_in_response.json()["refresh_token"]

    first_refresh_response = await client.post(
        "/api/v1/refresh", json={"refresh_token": first_refresh_token}
    )
    new_refresh_token = first_refresh_response.json()["refresh_token"]

    second_refresh_response = await client.post(
        "/api/v1/refresh", json={"refresh_token": new_refresh_token}
    )
    assert second_refresh_response.status_code == 200


async def test_refresh_fails_once_absolute_session_lifetime_elapsed(
    client: AsyncClient, redis_client: fakeredis.FakeAsyncRedis
) -> None:
    """Rotation alone keeps a session alive indefinitely while the user stays active;
    the absolute session lifetime caps it regardless. Here we simulate it having
    elapsed (deleting the session_start marker) rather than waiting out the real TTL —
    the token being refreshed is otherwise perfectly valid and non-rotated."""
    user_response = await register_user(client)
    user_id = user_response.json()["id"]
    user_email = user_response.json()["email"]

    logged_in_response = await client.post(
        "/api/v1/login", json={"email": user_email, "password": "password"}
    )
    refresh_token = logged_in_response.json()["refresh_token"]

    await redis_client.delete(f"refresh_token:session_start:{user_id}")

    response = await client.post("/api/v1/refresh", json={"refresh_token": refresh_token})
    assert response.status_code == 401


async def test_login_again_invalidates_previous_refresh_token(client: AsyncClient) -> None:
    """Logging in a second time replaces the refresh token: trying to refresh with
    the first (now-superseded) token → 401."""
    user_response = await register_user(client)
    user_email = user_response.json()["email"]
    user_password = "password"

    logged_in_response = await client.post(
        "/api/v1/login", json={"email": user_email, "password": user_password}
    )
    old_refresh_token = logged_in_response.json()["refresh_token"]

    # Login again
    await client.post("/api/v1/login", json={"email": user_email, "password": user_password})

    response = await client.post("/api/v1/refresh", json={"refresh_token": old_refresh_token})
    assert response.status_code == 401


async def test_logout_success(authenticated_client: AsyncClient) -> None:
    """POST /api/v1/logout with a valid access token → 204."""
    response = await authenticated_client.post("/api/v1/logout")
    assert response.status_code == 204


async def test_logout_revokes_refresh_token(authenticated_client: AsyncClient) -> None:
    """After logout, the refresh token that was active for this session no longer
    works (POST /api/v1/refresh with it → 401)."""
    response = await authenticated_client.post(
        "/api/v1/login", json={"email": "user@test.com", "password": "secret123"}
    )
    refresh_token = response.json()["refresh_token"]

    response = await authenticated_client.post("/api/v1/logout")
    assert response.status_code == 204

    response = await authenticated_client.post(
        "/api/v1/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 401


async def test_logout_without_token_returns_401(client: AsyncClient) -> None:
    """POST /api/v1/logout with no Authorization header at all → 401."""
    response = await client.post("/api/v1/logout")
    assert response.status_code == 401
