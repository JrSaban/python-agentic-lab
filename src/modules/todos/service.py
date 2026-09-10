from collections.abc import Sequence

from src.core.exceptions import NotFoundError
from src.modules.categories.repository import CategoryRepository
from src.modules.todos.models import Todo
from src.modules.todos.repository import TodoRepository
from src.modules.todos.schemas import TodoCreate, TodoUpdate

r"""
Service Layer (Logique métier pour les Todos).
Équivalent d'une classe TodoService ou d'Actions Laravel (App\Actions\CreateTodoAction).
"""


class TodoService:
    def __init__(self, repository: TodoRepository, category_repository: CategoryRepository) -> None:
        self.repository = repository
        self.category_repository = category_repository

    async def list_todos(
        self,
        skip: int = 0,
        limit: int = 100,
        is_completed: bool | None = None,
        category_ids: list[int] | None = None,
    ) -> Sequence[Todo]:
        """Récupère l'ensemble des todos avec pagination."""
        return await self.repository.get_all(
            skip=skip, limit=limit, is_completed=is_completed, category_ids=category_ids
        )

    async def get_todo_or_404(self, todo_id: int, with_categories: bool = False) -> Todo:
        """Récupère une tâche ou lève une exception HTTP 404."""
        todo = await self.repository.get_by_id(todo_id, with_categories=with_categories)
        if not todo:
            raise NotFoundError(f"Tâche avec l'ID {todo_id} introuvable.")
        return todo

    async def create_todo(self, data: TodoCreate) -> Todo:
        """Crée une nouvelle tâche."""
        categories = await self.category_repository.get_by_ids(data.category_ids)
        return await self.repository.create(data, categories)

    async def update_todo(self, todo_id: int, data: TodoUpdate) -> Todo:
        """Met à jour une tâche existante."""
        todo = await self.get_todo_or_404(todo_id, with_categories=data.category_ids is not None)

        categories = None
        if data.category_ids is not None:
            categories = await self.category_repository.get_by_ids(data.category_ids)

        return await self.repository.update(todo, data, categories)

    async def delete_todo(self, todo_id: int) -> None:
        """Supprime une tâche existante."""
        todo = await self.get_todo_or_404(todo_id)
        await self.repository.delete(todo)
