from collections.abc import Sequence
from typing import Annotated
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db_session
from src.modules.todos.models import Todo
from src.modules.todos.repository import TodoRepository
from src.modules.todos.schemas import TodoCreate, TodoResponse, TodoUpdate
from src.modules.todos.service import TodoService

"""
Routing & Controller Layer pour le domaine Todos.
Équivalent de routes/api.php et TodoController.php dans Laravel.
"""

router = APIRouter(prefix="/todos", tags=["Todos"])


# Factory de dépendance : instancie Repository et Service injectés par requête
def get_todo_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TodoService:
    repository = TodoRepository(session)
    return TodoService(repository)


# Type alias pour injection propre et lisible (standard Python moderne)
TodoServiceDep = Annotated[TodoService, Depends(get_todo_service)]


@router.get(
    "",
    response_model=list[TodoResponse],
    summary="Lister toutes les tâches",
    description="Retourne une liste paginée de tâches.",
)
async def list_todos(
    service: TodoServiceDep,
    skip: Annotated[int, Query(ge=0, description="Nombre d'éléments à sauter")] = 0,
    limit: Annotated[int, Query(ge=1, le=100, description="Nombre max d'éléments")] = 50,
) -> Sequence[Todo]:
    return await service.list_todos(skip=skip, limit=limit)


@router.post(
    "",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une tâche",
    description="Crée une nouvelle tâche et la persiste en base de données.",
)
async def create_todo(
    data: TodoCreate,
    service: TodoServiceDep,
) -> Todo:
    return await service.create_todo(data)


@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Afficher une tâche",
    description="Récupère les détails d'une tâche par son ID.",
)
async def get_todo(
    todo_id: int,
    service: TodoServiceDep,
) -> Todo:
    return await service.get_todo_or_404(todo_id)


@router.patch(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Mettre à jour une tâche",
    description="Met à jour partiellement les champs d'une tâche existante.",
)
async def update_todo(
    todo_id: int,
    data: TodoUpdate,
    service: TodoServiceDep,
) -> Todo:
    return await service.update_todo(todo_id, data)


@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une tâche",
    description="Supprime définitivement une tâche de la base de données.",
)
async def delete_todo(
    todo_id: int,
    service: TodoServiceDep,
) -> None:
    await service.delete_todo(todo_id)
