"""
Repository Pattern pour l'accès aux données de Category.
Encapsule les requêtes SQL (SQLAlchemy 2.0 select, add, delete).
"""

from collections.abc import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.modules.categories.models import Category
from src.modules.categories.schemas import CategoryCreate, CategoryUpdate


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(
        self, skip: int = 0, limit: int = 100, name: str | None = None
    ) -> Sequence[Category]:
        """Récupère une liste paginée de catégories."""
        query = select(Category).offset(skip).limit(limit).order_by(Category.name.asc())
        query = self._apply_filters(query, name=name)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, entity_id: int) -> Category | None:
        """Récupère une catégorie par son identifiant unique."""
        query = select(Category).where(Category.id == entity_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_ids(self, entity_ids: Sequence[int]) -> Sequence[Category]:
        """Récupère une liste de catégories par leurs identifiants."""
        if not entity_ids:
            return []

        query = select(Category).where(Category.id.in_(entity_ids))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_name(self, name: str) -> Category | None:
        """Récupère une catégorie par son nom."""
        query = select(Category).where(func.lower(Category.name) == func.lower(name))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: CategoryCreate) -> Category:
        """Crée et persiste une nouvelle catégorie."""
        category = Category(
            name=data.name,
            color=data.color,
        )
        self.session.add(category)
        # Génère l'ID via PostgreSQL sans commiter la transaction globale
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def update(self, category: Category, data: CategoryUpdate) -> Category:
        """Met à jour une catégorie existante avec les champs fournis."""
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)

        self.session.add(category)
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def delete(self, category: Category) -> None:
        """Supprime une catégorie de la base de données."""
        await self.session.delete(category)
        await self.session.flush()

    async def count(self, name: str | None = None) -> int:
        """Compte le nombre de catégories."""
        query = select(func.count()).select_from(Category)
        query = self._apply_filters(query, name=name)
        result = await self.session.execute(query)
        return result.scalar_one()

    def _apply_filters(
        self,
        query: Select,
        name: str | None = None,
    ) -> Select:
        """Helper qui applique les filtres sur une requête."""
        if name is not None:
            query = query.where(Category.name.ilike(f"%{name}%"))
        return query
