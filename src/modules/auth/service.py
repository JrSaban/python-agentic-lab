"""Service Layer (Logique métier pour l'auth)."""

from src.core.exceptions import UnauthorizedError
from src.core.security import create_access_token, verify_password
from src.modules.auth.schemas import LoginRequest, TokenResponse
from src.modules.users.repository import UserRepository


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Login a user."""
        user = await self.user_repository.get_by_email(data.email)

        if user is None or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("Email ou mot de passe incorrect")
        if not user.is_active:
            raise UnauthorizedError("Votre compte n'est pas actif")

        await self.user_repository.update_last_login_date(user)

        access_token = create_access_token({"sub": str(user.id)})
        return TokenResponse(access_token=access_token)
