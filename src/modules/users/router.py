"""Routing & Controller Layer pour le domaine Users."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.users.models import User
from src.modules.users.repository import UserRepository
from src.modules.users.schemas import UserCreate, UserResponse
from src.modules.users.service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


# Factory de dépendance : instancie Repository et Service injectés par requête
def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserService:
    repository = UserRepository(session)
    return UserService(repository)


# Type alias pour injection propre et lisible (standard Python moderne)
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un utilisateur",
    description="Crée un nouvel utilisateur et la persiste en base de données.",
)
async def create_user(
    service: UserServiceDep,
    data: UserCreate,
) -> User:
    return await service.create_user(data)
