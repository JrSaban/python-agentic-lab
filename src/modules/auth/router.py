"""Routing & Controller Layer pour le domaine Auth."""

from typing import Annotated

import jwt
from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.exceptions import UnauthorizedError
from src.core.security import decode_access_token
from src.modules.auth.schemas import LoginRequest, TokenResponse
from src.modules.auth.service import AuthService
from src.modules.users.models import User
from src.modules.users.repository import UserRepository

router = APIRouter(tags=["Auth"])

bearer_scheme = HTTPBearer()


# Dependency pour injecter l'utilisateur connecté
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as jwt_error:
        raise UnauthorizedError("Token invalide ou expiré.") from jwt_error

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Token invalide.")

    user_repository = UserRepository(session)
    user = await user_repository.get_by_id(int(user_id))
    if user is None or not user.is_active:
        raise UnauthorizedError("Utilisateur introuvable ou inactif.")

    return user


# Factory de dépendance : instancie Repository et Service injectés par requête
def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthService:
    user_repository = UserRepository(session)
    return AuthService(user_repository)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
# Type alias pour injection propre et lisible (standard Python moderne)
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login un utilisateur",
    description="Connecte un utilisateur et retourne un token.",
)
async def login(
    service: AuthServiceDep,
    data: LoginRequest,
) -> TokenResponse:
    return await service.login(data)
