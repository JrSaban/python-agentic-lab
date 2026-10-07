"""
Repository Pattern pour l'accès aux données de Category.
Encapsule les requêtes SQL (SQLAlchemy 2.0 select, add, delete).
"""

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repository import FilterParams, SoftDeleteRepository
from src.modules.categories.models import Category
from src.modules.categories.schemas import CategoryCreate


class CategoryRepository(SoftDeleteRepository[Category]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Category)

    async def get_all(
        self, skip: int = 0, limit: int = 25, name: str | None = None
    ) -> Sequence[Category]:
        """Récupère une liste paginée de catégories."""
        query = select(Category).order_by(Category.name.asc())
        query = self._apply_filters(query, name=name)

        return await self.paginate(query, skip, limit)

    async def get_by_id(self, entity_id: int) -> Category | None:
        """Get model's entity by its ID"""
        query = select(Category).where(Category.id == entity_id, Category.deleted_at.is_(None))

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_ids(self, entity_ids: Sequence[int]) -> Sequence[Category]:
        """Récupère une liste de catégories par leurs identifiants."""
        if not entity_ids:
            return []

        query = select(Category).where(Category.id.in_(entity_ids), Category.deleted_at.is_(None))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, created_by_id: int, data: CategoryCreate) -> Category:
        """Crée et persiste une nouvelle catégorie."""
        category = Category(
            name=data.name,
            color=data.color,
            created_by_id=created_by_id,
        )
        self.session.add(category)
        # Génère l'ID via PostgreSQL sans commiter la transaction globale
        await self.session.flush()
        await self.session.refresh(category)
        return category

    async def delete(self, entity: Category) -> None:
        """Soft delete the entity by setting the deleted_at field to the current time."""
        entity.deleted_at = datetime.now(UTC)
        self.session.add(entity)
        await self.session.flush()

    async def count(self, name: str | None = None) -> int:
        """Compte le nombre de catégories."""
        query = select(func.count()).select_from(Category)
        query = self._apply_filters(query, name=name)
        return await self.count_query(query)

    def _apply_filters(
        self,
        query: Select,
        name: str | None = None,
    ) -> Select:
        """Helper qui applique les filtres sur une requête."""
        query = self._apply_filter_params(
            query, [FilterParams(column=Category.name, value=name, op="ilike")]
        )
        query = query.where(Category.deleted_at.is_(None))
        return query
