"""
Routing & Controller Layer pour le domaine Categories.
"""

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.schemas import PaginatedResponse
from src.modules.categories.models import Category
from src.modules.categories.repository import CategoryRepository
from src.modules.categories.schemas import CategoryCreate, CategoryResponse, CategoryUpdate
from src.modules.categories.service import CategoryService
from src.modules.todos.models import Todo
from src.modules.todos.schemas import TodoResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


# Factory de dépendance : instancie Repository et Service injectés par requête
def get_category_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CategoryService:
    repository = CategoryRepository(session)
    return CategoryService(repository)


# Type alias pour injection propre et lisible (standard Python moderne)
CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]


@router.get(
    "",
    response_model=PaginatedResponse[CategoryResponse],
    summary="Lister toutes les catégories",
    description="Retourne une liste paginée de catégories.",
)
async def list_categories(
    service: CategoryServiceDep,
    skip: Annotated[int, Query(ge=0, description="Nombre d'éléments à sauter")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Nombre max d'éléments")] = 50,
    name: Annotated[str | None, Query(min_length=2, description="Filtre sur le nom")] = None,
) -> PaginatedResponse[CategoryResponse]:
    categories, total = await service.list_categories(skip=skip, limit=limit, name=name)
    return PaginatedResponse(items=categories, total=total, skip=skip, limit=limit)


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une catégorie.",
    description="Crée une nouvelle catégorie.",
)
async def create_category(
    service: CategoryServiceDep,
    data: CategoryCreate,
) -> Category:
    return await service.create_category(data)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Afficher une catégorie",
    description="Récupère les détails d'une catégorie par son ID. ",
)
async def get_category(
    service: CategoryServiceDep,
    category_id: int,
) -> Category:
    return await service.get_category_or_404(category_id)


@router.get(
    "/{category_id}/todos",
    response_model=list[TodoResponse],
    summary="Lister les tâches d'une catégorie",
    description="Récupère toutes les tâches associées à une catégorie.",
)
async def list_todos_by_category(
    service: CategoryServiceDep,
    category_id: int,
) -> Sequence[Todo]:
    category = await service.get_category_or_404(category_id, with_todos=True)
    return category.todos


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    summary="Mettre à jour une catégorie",
    description="Met à jour partiellement les champs d'une catégorie existante.",
)
async def update_category(
    service: CategoryServiceDep,
    category_id: int,
    data: CategoryUpdate,
) -> Category:
    return await service.update_category(category_id, data)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une catégorie.",
    description="Supprime définitivement une catégorie de la base de données.",
)
async def delete_category(
    service: CategoryServiceDep,
    category_id: int,
) -> None:
    await service.delete_category(category_id)
