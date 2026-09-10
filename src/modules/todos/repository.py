"""
Repository Pattern pour l'accès aux données de Todo.
Encapsule les requêtes SQL (SQLAlchemy 2.0 select, add, delete).
"""

from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.modules.categories.models import Category
from src.modules.todos.models import Todo
from src.modules.todos.schemas import TodoCreate, TodoUpdate


class TodoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        is_completed: bool | None = None,
        category_ids: list[int] | None = None,
    ) -> Sequence[Todo]:
        """Récupère une liste paginée de tâches."""
        query = select(Todo).offset(skip).limit(limit).order_by(Todo.id.desc())
        query = self._apply_filters(query, is_completed, category_ids)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, entity_id: int, with_categories: bool = False) -> Todo | None:
        """Récupère une tâche par son identifiant unique."""
        query = select(Todo).where(Todo.id == entity_id)

        if with_categories:
            query = query.options(selectinload(Todo.categories))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: TodoCreate, categories: Sequence[Category]) -> Todo:
        """Crée et persiste une nouvelle tâche."""
        todo = Todo(
            title=data.title,
            description=data.description,
            categories=list(categories),
        )
        self.session.add(todo)
        # Génère l'ID via PostgreSQL sans commiter la transaction globale
        await self.session.flush()
        await self.session.refresh(todo)
        return todo

    async def update(
        self, todo: Todo, data: TodoUpdate, categories: Sequence[Category] | None = None
    ) -> Todo:
        """Met à jour une tâche existante avec les champs fournis."""
        update_data = data.model_dump(exclude_unset=True, exclude={"category_ids"})
        for field, value in update_data.items():
            setattr(todo, field, value)

        if categories is not None:
            todo.categories = list(categories)

        self.session.add(todo)
        await self.session.flush()
        await self.session.refresh(todo)
        return todo

    async def delete(self, todo: Todo) -> None:
        """Supprime une tâche de la base de données."""
        await self.session.delete(todo)
        await self.session.flush()

    async def count(
        self, is_completed: bool | None = None, category_ids: list[int] | None = None
    ) -> int:
        query = select(func.count()).select_from(Todo)
        query = self._apply_filters(query, is_completed, category_ids)

        result = await self.session.execute(query)
        return result.scalar_one()

    def _apply_filters(
        self, query: Select, is_completed: bool | None = None, category_ids: list[int] | None = None
    ) -> Select:
        """Helper qui applique les filtres sur une requête."""
        if is_completed is not None:
            query = query.where(Todo.is_completed == is_completed)
        if category_ids is not None:
            query = query.where(Todo.categories.any(Category.id.in_(category_ids)))
        return query
