from unittest.mock import AsyncMock, patch

import pytest

from src.core.exceptions import UnauthorizedError
from src.modules.auth.schemas import LoginRequest
from src.modules.auth.service import AuthService
from src.modules.users.models import User


@patch("src.modules.auth.service.create_access_token", return_value="token")
@patch("src.modules.auth.service.verify_password", return_value=True)
async def test_login_success(mock_verify_password, mock_create_access_token):
    mock_user_repo = AsyncMock()
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=True,
        hashed_password="hashed_password",
    )
    mock_user_repo.get_by_email.return_value = user
    auth_service = AuthService(mock_user_repo)
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
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=True,
        hashed_password="hashed_password",
    )
    mock_user_repo.get_by_email.return_value = user
    auth_service = AuthService(mock_user_repo)
    login_request = LoginRequest(email="test@gmail.com", password="wrong_password")

    with pytest.raises(UnauthorizedError):
        await auth_service.login(login_request)

    mock_verify_password.assert_called_once_with(login_request.password, user.hashed_password)
    mock_user_repo.get_by_email.assert_called_once_with(login_request.email)
    mock_user_repo.update_last_login_date.assert_not_called()


@patch("src.modules.auth.service.verify_password")
async def test_login_user_not_found_raises_unauthorized_error(mock_verify_password):
    mock_user_repo = AsyncMock()
    mock_user_repo.get_by_email.return_value = None
    auth_service = AuthService(mock_user_repo)
    login_request = LoginRequest(email="test@gmail.com", password="password")

    with pytest.raises(UnauthorizedError):
        await auth_service.login(login_request)

    mock_verify_password.assert_not_called()
    mock_user_repo.get_by_email.assert_called_once_with(login_request.email)
    mock_user_repo.update_last_login_date.assert_not_called()


@patch("src.modules.auth.service.verify_password", return_value=True)
async def test_login_user_not_active_raises_unauthorized_error(mock_verify_password):
    mock_user_repo = AsyncMock()
    user = User(
        id=1,
        email="test@gmail.com",
        is_active=False,
        hashed_password="hashed_password",
    )
    mock_user_repo.get_by_email.return_value = user
    auth_service = AuthService(mock_user_repo)
    login_request = LoginRequest(email="test@gmail.com", password="password")

    with pytest.raises(UnauthorizedError):
        await auth_service.login(login_request)

    assert not user.is_active
    mock_verify_password.assert_called_once_with(login_request.password, user.hashed_password)
    mock_user_repo.get_by_email.assert_called_once_with(login_request.email)
    mock_user_repo.update_last_login_date.assert_not_called()
