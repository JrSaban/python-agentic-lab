"""
Service Layer (Logique métier pour les Categories).
"""

from collections.abc import Sequence

from src.core.exceptions import ConflictError, NotFoundError
from src.modules.categories.models import Category
from src.modules.categories.repository import CategoryRepository
from src.modules.categories.schemas import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, repository: CategoryRepository) -> None:
        self.repository = repository

    async def list_categories(self, skip: int = 0, limit: int = 100) -> Sequence[Category]:
        """Récupère l'ensemble des catégories avec pagination."""
        return await self.repository.get_all(skip=skip, limit=limit)

    async def get_category_or_404(self, entity_id: int, with_todos: bool = False) -> Category:
        """Récupère une catégorie ou lève une exception HTTP 404."""
        category = await self.repository.get_by_id(entity_id, with_todos=with_todos)
        if not category:
            raise NotFoundError(f"Catégorie avec l'ID {entity_id} introuvable.")
        return category

    async def create_category(self, data: CategoryCreate) -> Category:
        """Crée une nouvelle catégorie."""
        category = await self.repository.get_by_name(data.name)
        if category:
            raise ConflictError(f"Une catégorie avec le nom {data.name} existe déjà.")
        return await self.repository.create(data)

    async def update_category(self, entity_id: int, data: CategoryUpdate) -> Category:
        """Met à jour une catégorie existante."""
        category = await self.get_category_or_404(entity_id, with_todos=False)

        if data.name is not None and category.name.lower() != data.name.lower():
            existing = await self.repository.get_by_name(data.name)
            if existing is not None:
                raise ConflictError(f"Une catégorie avec le nom {data.name} existe déjà.")

        return await self.repository.update(category, data)

    async def delete_category(self, entity_id: int) -> None:
        """Supprime une categorie existante."""
        category = await self.get_category_or_404(entity_id)
        await self.repository.delete(category)
