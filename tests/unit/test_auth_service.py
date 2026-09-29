from unittest.mock import AsyncMock, patch

import pytest

from src.core.exceptions import UnauthorizedError
from src.modules.auth.schemas import LoginRequest, RefreshTokenRequest
from src.modules.auth.service import AuthService
from src.modules.users.models import User


@patch("src.modules.auth.service.create_access_token", return_value="token")
@patch("src.modules.auth.service.verify_password", return_value=True)
async def test_login_success(mock_verify_password, mock_create_access_token):
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=True,
        hashed_password="hashed_password",
    )
    mock_user_repo.get_by_email.return_value = user
    auth_service = AuthService(mock_user_repo, mock_redis_client)
    login_request = LoginRequest(email="test@gmail.com", password="password")

    result = await auth_service.login(login_request)

    assert result.access_token == "token"
    mock_verify_password.assert_called_once_with(login_request.password, user.hashed_password)
    mock_create_access_token.assert_called_once_with({"sub": str(user.id)})
    mock_user_repo.get_by_email.assert_called_once_with(login_request.email)
    mock_user_repo.update_last_login_date.assert_called_once_with(user)


@patch("src.modules.auth.service.verify_password", return_value=False)
async def test_login_wrong_password_raises_unauthorized_error(mock_verify_password):
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=True,
        hashed_password="hashed_password",
    )
    mock_user_repo.get_by_email.return_value = user
    auth_service = AuthService(mock_user_repo, mock_redis_client)
    login_request = LoginRequest(email="test@gmail.com", password="wrong_password")

    with pytest.raises(UnauthorizedError):
        await auth_service.login(login_request)

    mock_verify_password.assert_called_once_with(login_request.password, user.hashed_password)
    mock_user_repo.get_by_email.assert_called_once_with(login_request.email)
    mock_user_repo.update_last_login_date.assert_not_called()


@patch("src.modules.auth.service.verify_password")
async def test_login_user_not_found_raises_unauthorized_error(mock_verify_password):
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_user_repo.get_by_email.return_value = None
    auth_service = AuthService(mock_user_repo, mock_redis_client)
    login_request = LoginRequest(email="test@gmail.com", password="password")

    with pytest.raises(UnauthorizedError):
        await auth_service.login(login_request)

    mock_verify_password.assert_not_called()
    mock_user_repo.get_by_email.assert_called_once_with(login_request.email)
    mock_user_repo.update_last_login_date.assert_not_called()


@patch("src.modules.auth.service.verify_password", return_value=True)
async def test_login_user_not_active_raises_unauthorized_error(mock_verify_password):
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=False,
        hashed_password="hashed_password",
    )
    mock_user_repo.get_by_email.return_value = user
    auth_service = AuthService(mock_user_repo, mock_redis_client)
    login_request = LoginRequest(email="test@gmail.com", password="password")

    with pytest.raises(UnauthorizedError):
        await auth_service.login(login_request)

    assert not user.is_active
    mock_verify_password.assert_called_once_with(login_request.password, user.hashed_password)
    mock_user_repo.get_by_email.assert_called_once_with(login_request.email)
    mock_user_repo.update_last_login_date.assert_not_called()


@patch("src.modules.auth.service.create_access_token", return_value="access_token")
@patch("src.modules.auth.service.verify_password", return_value=True)
async def test_login_replaces_existing_refresh_token(
    mock_verify_password, mock_create_access_token
):
    """A second login for the same user deletes the previous refresh token's Redis
    entries before storing the new pair."""
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=True,
    )
    mock_user_repo.get_by_email.return_value = user
    mock_redis_client.get.return_value = "old_token_value"
    auth_service = AuthService(mock_user_repo, mock_redis_client)
    login_request = LoginRequest(email="test@gmail.com", password="password")

    await auth_service.login(login_request)

    mock_redis_client.get.assert_called_once_with("refresh_token:user:1")
    assert mock_redis_client.delete.call_count == 2
    mock_redis_client.delete.assert_any_call("refresh_token:token:old_token_value")
    mock_redis_client.delete.assert_any_call("refresh_token:user:1")


@patch("src.modules.auth.service.create_access_token", return_value="new_access_token")
async def test_refresh_success(mock_create_access_token):
    """A valid, still-stored refresh token returns a new access token and the same
    refresh token, without touching its Redis entries (no rotation)."""
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=True,
    )
    mock_user_repo.get_by_id.return_value = user
    mock_redis_client.get.return_value = "1"
    auth_service = AuthService(mock_user_repo, mock_redis_client)
    data_request = RefreshTokenRequest(refresh_token="refresh_token")

    result = await auth_service.refresh(data_request.refresh_token)

    mock_redis_client.get.assert_called_once_with("refresh_token:token:refresh_token")
    mock_redis_client.set.assert_not_called()
    assert result.access_token == "new_access_token"
    assert result.refresh_token == "refresh_token"


async def test_refresh_unknown_token_raises_unauthorized_error():
    """A refresh token absent from Redis (never issued, expired, or already revoked)
    raises UnauthorizedError."""
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_redis_client.get.return_value = None
    auth_service = AuthService(mock_user_repo, mock_redis_client)
    data_request = RefreshTokenRequest(refresh_token="refresh_token")

    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(data_request.refresh_token)

    mock_redis_client.get.assert_called_once_with("refresh_token:token:refresh_token")
    mock_redis_client.set.assert_not_called()
    mock_user_repo.get_by_id.assert_not_called()


async def test_refresh_user_not_found_raises_unauthorized_error():
    """A refresh token found in Redis, but whose user no longer exists in the
    database, raises UnauthorizedError."""
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    mock_user_repo.get_by_id.return_value = None
    mock_redis_client.get.return_value = "1"
    auth_service = AuthService(mock_user_repo, mock_redis_client)
    data_request = RefreshTokenRequest(refresh_token="refresh_token")

    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(data_request.refresh_token)

    mock_redis_client.get.assert_called_once_with("refresh_token:token:refresh_token")
    mock_redis_client.set.assert_not_called()
    mock_user_repo.get_by_id.assert_called_once_with(1)


async def test_refresh_user_not_active_raises_unauthorized_error():
    """A refresh token found in Redis, but belonging to a deactivated user, raises
    UnauthorizedError — being technically valid in Redis isn't enough."""
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=False,
    )
    mock_user_repo.get_by_id.return_value = user
    mock_redis_client.get.return_value = "1"
    auth_service = AuthService(mock_user_repo, mock_redis_client)
    data_request = RefreshTokenRequest(refresh_token="refresh_token")

    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(data_request.refresh_token)

    mock_redis_client.get.assert_called_once_with("refresh_token:token:refresh_token")
    mock_redis_client.set.assert_not_called()
    mock_user_repo.get_by_id.assert_called_once_with(1)


async def test_logout_deletes_refresh_token():
    """Logging out deletes both Redis entries (user → token and token → user) for
    the current user's refresh token."""
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=True,
    )
    mock_redis_client.get.return_value = "refresh_token"
    auth_service = AuthService(mock_user_repo, mock_redis_client)

    await auth_service.logout(user)

    mock_redis_client.get.assert_called_once_with("refresh_token:user:1")
    assert mock_redis_client.delete.call_count == 2
    mock_redis_client.delete.assert_any_call("refresh_token:user:1")
    mock_redis_client.delete.assert_any_call("refresh_token:token:refresh_token")


async def test_logout_without_existing_refresh_token_does_nothing():
    """Logging out a user who has no stored refresh token (already logged out, or
    never logged in) doesn't raise."""
    mock_user_repo = AsyncMock()
    mock_redis_client = AsyncMock()
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=True,
    )
    mock_redis_client.get.return_value = None
    auth_service = AuthService(mock_user_repo, mock_redis_client)

    await auth_service.logout(user)

    mock_redis_client.get.assert_called_once_with("refresh_token:user:1")
    mock_redis_client.set.assert_not_called()
    mock_redis_client.delete.assert_not_called()
