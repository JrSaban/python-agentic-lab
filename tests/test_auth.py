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
