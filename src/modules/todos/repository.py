"""
Repository Pattern pour l'accès aux données de Todo.
Encapsule les requêtes SQL (SQLAlchemy 2.0 select, add, delete).
"""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.todos.models import Todo
from src.modules.todos.schemas import TodoCreate, TodoUpdate


class TodoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[Todo]:
        """Récupère une liste paginée de tâches."""
        query = select(Todo).offset(skip).limit(limit).order_by(Todo.id.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, entity_id: int) -> Todo | None:
        """Récupère une tâche par son identifiant unique."""
        query = select(Todo).where(Todo.id == entity_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: TodoCreate) -> Todo:
        """Crée et persiste une nouvelle tâche."""
        todo = Todo(
            title=data.title,
            description=data.description,
        )
        self.session.add(todo)
        # Génère l'ID via PostgreSQL sans commiter la transaction globale
        await self.session.flush()
        await self.session.refresh(todo)
        return todo

    async def update(self, todo: Todo, data: TodoUpdate) -> Todo:
        """Met à jour une tâche existante avec les champs fournis."""
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(todo, field, value)

        self.session.add(todo)
        await self.session.flush()
        await self.session.refresh(todo)
        return todo

    async def delete(self, todo: Todo) -> None:
        """Supprime une tâche de la base de données."""
        await self.session.delete(todo)
        await self.session.flush()
