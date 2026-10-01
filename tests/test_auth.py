"""Tests d'intégration de l'endpoint Auth."""

from httpx import AsyncClient, Response
from sqlalchemy.ext.asyncio import AsyncSession

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
