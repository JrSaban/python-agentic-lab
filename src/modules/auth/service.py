"""Service Layer (Logique métier pour l'auth)."""

from datetime import timedelta
from typing import Literal, cast

from redis.asyncio import Redis

from src.core.config import settings
from src.core.exceptions import UnauthorizedError
from src.core.security import create_access_token, generate_refresh_token, verify_password
from src.modules.auth.schemas import LoginRequest, TokenResponse
from src.modules.users.models import User
from src.modules.users.repository import UserRepository


class AuthService:
    def __init__(self, user_repository: UserRepository, redis_client: Redis) -> None:
        self.user_repository = user_repository
        self.redis_client = redis_client

    def _cache_key(self, key: Literal["user", "token"], value: int | str) -> str:
        return f"refresh_token:{key}:{value}"

    async def _revoke_refresh_token(self, user_id: int) -> None:
        """Revoke all refresh tokens for a user."""
        user_key = self._cache_key("user", user_id)
        old_token = cast(str | None, await self.redis_client.get(user_key))

        if old_token is not None:
            await self.redis_client.delete(self._cache_key("token", old_token))
            await self.redis_client.delete(user_key)

    async def _store_or_replace_refresh_token(self, user_id: int, refresh_token: str) -> None:
        """Store or replace the refresh token for a user."""
        user_key = self._cache_key("user", user_id)
        new_token_key = self._cache_key("token", refresh_token)

        await self._revoke_refresh_token(user_id)

        await self.redis_client.set(
            user_key, refresh_token, ex=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        )
        await self.redis_client.set(
            new_token_key, user_id, ex=timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        )

    async def login(self, data: LoginRequest) -> TokenResponse:
        """Login a user."""
        user = await self.user_repository.get_by_email(data.email)

        if user is None or not verify_password(data.password, user.hashed_password):
            raise UnauthorizedError("Email ou mot de passe incorrect")
        if not user.is_active:
            raise UnauthorizedError("Votre compte n'est pas actif")

        await self.user_repository.update_last_login_date(user)

        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = generate_refresh_token()

        await self._store_or_replace_refresh_token(user.id, refresh_token)

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Refresh a user token."""
        user_id = cast(
            str | None, await self.redis_client.get(self._cache_key("token", refresh_token))
        )
        if user_id is None:
            raise UnauthorizedError("Refresh token invalide ou expiré")

        user = await self.user_repository.get_by_id(int(user_id))
        if user is None or not user.is_active:
            raise UnauthorizedError("Refresh token invalide ou expiré")

        access_token = create_access_token({"sub": str(user.id)})

        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    async def logout(self, user: User) -> None:
        await self._revoke_refresh_token(user.id)
