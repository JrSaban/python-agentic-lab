"""
Service Layer (Logique métier pour les Categories).
"""

from collections.abc import Sequence

from fastapi import HTTPException, status
from src.modules.categories.models import Category
from src.modules.categories.repository import CategoryRepository
from src.modules.categories.schemas import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, repository: CategoryRepository) -> None:
        self.repository = repository

    async def list_categories(self, skip: int = 0, limit: int = 100) -> Sequence[Category]:
        """Récupère l'ensemble des categories avec pagination."""
        return await self.repository.get_all(skip=skip, limit=limit)

    async def get_category_or_404(self, entity_id: int) -> Category:
        """Récupère une categorie ou lève une exception HTTP 404."""
        category = await self.repository.get_by_id(entity_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Category avec l'ID {entity_id} introuvable.",
            )
        return category

    async def create_category(self, data: CategoryCreate) -> Category:
        """Crée une nouvelle categorie."""
        category = await self.repository.get_by_name(data.name)
        if category:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Une categorie avec le nom {data.name} existe deja.",
            )
        return await self.repository.create(data)

    async def update_category(self, entity_id: int, data: CategoryUpdate) -> Category:
        """Met à jour une categorie existante."""
        category = await self.get_category_or_404(entity_id)

        if data.name is not None and category.name.lower() != data.name.lower():
            existing = await self.repository.get_by_name(data.name)
            if existing is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Une categorie avec le nom {data.name} existe deja.",
                )

        return await self.repository.update(category, data)

    async def delete_category(self, entity_id: int) -> None:
        """Supprime une categorie existante."""
        category = await self.get_category_or_404(entity_id)
        await self.repository.delete(category)
