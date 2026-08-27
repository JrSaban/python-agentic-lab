from os import name
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.modules.categories.models import Category
from src.modules.categories.schemas import CategoryCreate, CategoryUpdate

"""
Repository Pattern pour l'accès aux données de Category.
Encapsule les requêtes SQL (SQLAlchemy 2.0 select, add, delete).
"""


class CategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[Category]:
        """Récupère une liste paginée de catégories."""
        query = select(Category).offset(skip).limit(limit).order_by(Category.name.asc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_id(self, entity_id: int) -> Category | None:
        """Récupère une categorie par son identifiant unique."""
        query = select(Category).where(Category.id == entity_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> Category | None:
        """Récupère une categorie par son nom."""
        query = select(Category).where(Category.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, data: CategoryCreate) -> Category:
        """Crée et persiste une nouvelle categorie."""
        category = Category(
            name=data.name,
            color=data.color,
        )
        self.session.add(category)
        await self.session.flush()    # Génère l'ID via PostgreSQL sans commiter la transaction globale
        await self.session.refresh(category)
        return category

    async def update(self, category: Category, data: CategoryUpdate) -> Category:
        """Met à jour une categorie existante avec les champs fournis."""
        update_data = data.model_dump(exclude_unset=True)  # Ne prend que les champs envoyés par le client
        
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
