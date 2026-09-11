"""
Routing & Controller Layer pour le domaine Todos.
Équivalent de routes/api.php et TodoController.php dans Laravel.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.core.schemas import PaginatedResponse
from src.modules.categories.repository import CategoryRepository
from src.modules.todos.models import Todo
from src.modules.todos.repository import TodoRepository
from src.modules.todos.schemas import TodoCreate, TodoDetailResponse, TodoResponse, TodoUpdate
from src.modules.todos.service import TodoService

router = APIRouter(prefix="/todos", tags=["Todos"])


# Factory de dépendance : instancie Repository et Service injectés par requête
def get_todo_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TodoService:
    repository = TodoRepository(session)
    category_repository = CategoryRepository(session)
    return TodoService(repository, category_repository)


# Type alias pour injection propre et lisible (standard Python moderne)
TodoServiceDep = Annotated[TodoService, Depends(get_todo_service)]


@router.get(
    "",
    response_model=PaginatedResponse[TodoResponse],
    summary="Lister toutes les tâches",
    description="Retourne une liste paginée de tâches.",
)
async def list_todos(
    service: TodoServiceDep,
    skip: Annotated[int, Query(ge=0, description="Nombre d'éléments à sauter")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Nombre max d'éléments")] = 50,
    name: Annotated[str | None, Query(min_length=2, description="Filtre sur le nom")] = None,
    is_completed: Annotated[
        bool | None, Query(description="Filtre sur le statut de complétion")
    ] = None,
    category_ids: Annotated[
        list[int] | None, Query(description="Filtre sur les catégories")
    ] = None,
) -> PaginatedResponse[TodoResponse]:
    todos, total = await service.list_todos(
        skip=skip, limit=limit, name=name, is_completed=is_completed, category_ids=category_ids
    )

    return PaginatedResponse(items=todos, total=total, skip=skip, limit=limit)


@router.post(
    "",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une tâche",
    description="Crée une nouvelle tâche et la persiste en base de données.",
)
async def create_todo(
    service: TodoServiceDep,
    data: TodoCreate,
) -> Todo:
    return await service.create_todo(data)


@router.get(
    "/{todo_id}",
    response_model=TodoResponse | TodoDetailResponse,
    summary="Afficher une tâche",
    description="Récupère une tâche. `?include=categories` pour inclure ses catégories.",
)
async def get_todo(
    service: TodoServiceDep,
    todo_id: int,
    include: Annotated[list[str] | None, Query()] = None,
) -> TodoResponse | TodoDetailResponse:
    with_categories = include is not None and "categories" in include
    todo = await service.get_todo_or_404(todo_id, with_categories)

    if with_categories:
        return TodoDetailResponse.model_validate(todo)
    return TodoResponse.model_validate(todo)


@router.patch(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Mettre à jour une tâche",
    description="Met à jour partiellement les champs d'une tâche existante.",
)
async def update_todo(
    service: TodoServiceDep,
    todo_id: int,
    data: TodoUpdate,
) -> Todo:
    return await service.update_todo(todo_id, data)


@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une tâche",
    description="Supprime définitivement une tâche de la base de données.",
)
async def delete_todo(
    service: TodoServiceDep,
    todo_id: int,
) -> None:
    await service.delete_todo(todo_id)
