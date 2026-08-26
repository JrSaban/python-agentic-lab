from collections.abc import Sequence
from fastapi import HTTPException, status
from src.modules.todos.models import Todo
from src.modules.todos.repository import TodoRepository
from src.modules.todos.schemas import TodoCreate, TodoUpdate

r"""
Service Layer (Logique métier pour les Todos).
Équivalent d'une classe TodoService ou d'Actions Laravel (App\Actions\CreateTodoAction).
"""


class TodoService:
    def __init__(self, repository: TodoRepository) -> None:
        self.repository = repository

    async def list_todos(self, skip: int = 0, limit: int = 100) -> Sequence[Todo]:
        """Récupère l'ensemble des todos avec pagination."""
        return await self.repository.get_all(skip=skip, limit=limit)

    async def get_todo_or_404(self, todo_id: int) -> Todo:
        """Récupère une tâche ou lève une exception HTTP 404."""
        todo = await self.repository.get_by_id(todo_id)
        if not todo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tâche avec l'ID {todo_id} introuvable.",
            )
        return todo

    async def create_todo(self, data: TodoCreate) -> Todo:
        """Crée une nouvelle tâche."""
        return await self.repository.create(data)

    async def update_todo(self, todo_id: int, data: TodoUpdate) -> Todo:
        """Met à jour une tâche existante."""
        todo = await self.get_todo_or_404(todo_id)
        return await self.repository.update(todo, data)

    async def delete_todo(self, todo_id: int) -> None:
        """Supprime une tâche existante."""
        todo = await self.get_todo_or_404(todo_id)
        await self.repository.delete(todo)
