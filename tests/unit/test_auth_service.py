import hashlib
from unittest.mock import AsyncMock, patch

import pytest

from src.core.exceptions import UnauthorizedError
from src.modules.auth.schemas import LoginRequest
from src.modules.auth.service import AuthService
from src.modules.users.models import User

LOGIN_REQUEST = LoginRequest(email="test@gmail.com", password="password")


def token_key(refresh_token: str) -> str:
    """Clé Redis attendue pour un refresh token en clair (le service ne stocke que son hash)."""
    return f"refresh_token:token:{hashlib.sha256(refresh_token.encode()).hexdigest()}"


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_redis() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def auth_service(mock_user_repo: AsyncMock, mock_redis: AsyncMock) -> AuthService:
    return AuthService(mock_user_repo, mock_redis)


@pytest.fixture
def user() -> User:
    return User(id=1, email="test@gmail.com", is_active=True, hashed_password="hashed_password")


# --- login ---


@patch("src.modules.auth.service.create_access_token", return_value="access_token")
@patch("src.modules.auth.service.verify_password", return_value=True)
async def test_login_success(
    mock_verify_password, mock_create_access_token, auth_service, mock_user_repo, mock_redis, user
):
    """A successful login returns both tokens, and stores the refresh token's hash in
    Redis — never the plain token."""
    mock_user_repo.get_by_email.return_value = user
    mock_redis.set.return_value = None

    result = await auth_service.login(LOGIN_REQUEST)

    assert result.access_token == "access_token"
    assert result.refresh_token
    mock_verify_password.assert_called_once_with(LOGIN_REQUEST.password, user.hashed_password)
    mock_create_access_token.assert_called_once_with({"sub": str(user.id)})
    mock_user_repo.update_last_login_date.assert_called_once_with(user)

    stored_keys = [c.args[0] for c in mock_redis.set.call_args_list]
    assert stored_keys == [token_key(result.refresh_token), "refresh_token:user:1"]
    assert result.refresh_token not in str(mock_redis.set.call_args_list)
    mock_redis.delete.assert_not_called()


@patch("src.modules.auth.service.verify_password", return_value=False)
async def test_login_wrong_password_raises_unauthorized_error(
    mock_verify_password, auth_service, mock_user_repo, mock_redis, user
):
    mock_user_repo.get_by_email.return_value = user

    with pytest.raises(UnauthorizedError):
        await auth_service.login(LOGIN_REQUEST)

    mock_verify_password.assert_called_once_with(LOGIN_REQUEST.password, user.hashed_password)
    mock_user_repo.update_last_login_date.assert_not_called()
    mock_redis.set.assert_not_called()


@patch("src.modules.auth.service.verify_password")
async def test_login_user_not_found_raises_unauthorized_error(
    mock_verify_password, auth_service, mock_user_repo, mock_redis
):
    mock_user_repo.get_by_email.return_value = None

    with pytest.raises(UnauthorizedError):
        await auth_service.login(LOGIN_REQUEST)

    mock_verify_password.assert_not_called()
    mock_user_repo.update_last_login_date.assert_not_called()
    mock_redis.set.assert_not_called()


@patch("src.modules.auth.service.verify_password", return_value=True)
async def test_login_user_not_active_raises_unauthorized_error(
    mock_verify_password, auth_service, mock_user_repo, mock_redis, user
):
    user.is_active = False
    mock_user_repo.get_by_email.return_value = user

    with pytest.raises(UnauthorizedError):
        await auth_service.login(LOGIN_REQUEST)

    mock_user_repo.update_last_login_date.assert_not_called()
    mock_redis.set.assert_not_called()


@patch("src.modules.auth.service.create_access_token", return_value="access_token")
@patch("src.modules.auth.service.verify_password", return_value=True)
async def test_login_replaces_existing_refresh_token(
    mock_verify_password, mock_create_access_token, auth_service, mock_user_repo, mock_redis, user
):
    """A second login atomically swaps the user's token (SET ... GET) and deletes the
    previous token's key. The new token key must be written *before* the swap, otherwise
    a concurrent login could delete it before it exists and leave an orphan."""
    mock_user_repo.get_by_email.return_value = user
    mock_redis.set.return_value = "old_hash"

    result = await auth_service.login(LOGIN_REQUEST)

    first_set, second_set = mock_redis.set.call_args_list
    assert first_set.args[0] == token_key(result.refresh_token)
    assert second_set.args[0] == "refresh_token:user:1"
    assert second_set.kwargs["get"] is True
    mock_redis.delete.assert_called_once_with("refresh_token:token:old_hash")


# --- refresh ---


@patch("src.modules.auth.service.create_access_token", return_value="new_access_token")
async def test_refresh_success(
    mock_create_access_token, auth_service, mock_user_repo, mock_redis, user
):
    """A valid, still-stored refresh token returns a new access token and the same
    refresh token, without touching its Redis entries (no rotation)."""
    mock_user_repo.get_by_id.return_value = user
    mock_redis.get.return_value = "1"

    result = await auth_service.refresh("refresh_token")

    mock_redis.get.assert_called_once_with(token_key("refresh_token"))
    mock_user_repo.get_by_id.assert_called_once_with(1)
    mock_create_access_token.assert_called_once_with({"sub": "1"})
    mock_redis.set.assert_not_called()
    assert result.access_token == "new_access_token"
    assert result.refresh_token == "refresh_token"


async def test_refresh_unknown_token_raises_unauthorized_error(
    auth_service, mock_user_repo, mock_redis
):
    """A refresh token absent from Redis (never issued, expired, or already revoked)
    raises UnauthorizedError without querying the database."""
    mock_redis.get.return_value = None

    with pytest.raises(UnauthorizedError):
        await auth_service.refresh("refresh_token")

    mock_redis.get.assert_called_once_with(token_key("refresh_token"))
    mock_user_repo.get_by_id.assert_not_called()


@pytest.mark.parametrize("user_state", ["deleted", "inactive"])
async def test_refresh_user_deleted_or_inactive_raises_unauthorized_error(
    user_state, auth_service, mock_user_repo, mock_redis, user
):
    """A refresh token found in Redis isn't enough on its own: its user must still
    exist and be active in the database."""
    user.is_active = False
    mock_user_repo.get_by_id.return_value = None if user_state == "deleted" else user
    mock_redis.get.return_value = "1"

    with pytest.raises(UnauthorizedError):
        await auth_service.refresh("refresh_token")

    mock_user_repo.get_by_id.assert_called_once_with(1)


# --- logout ---


async def test_logout_deletes_refresh_token(auth_service, mock_redis, user):
    """Logging out atomically reads and deletes the user's key (GETDEL), then deletes
    the token key it pointed to."""
    mock_redis.getdel.return_value = "stored_hash"

    await auth_service.logout(user)

    mock_redis.getdel.assert_called_once_with("refresh_token:user:1")
    mock_redis.delete.assert_called_once_with("refresh_token:token:stored_hash")


async def test_logout_without_existing_refresh_token_does_nothing(auth_service, mock_redis, user):
    """Logging out a user with no stored refresh token (already logged out, or never
    logged in) doesn't raise and deletes nothing."""
    mock_redis.getdel.return_value = None

    await auth_service.logout(user)

    mock_redis.getdel.assert_called_once_with("refresh_token:user:1")
    mock_redis.delete.assert_not_called()
