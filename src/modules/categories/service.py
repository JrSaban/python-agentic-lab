"""
Service Layer (Logique métier pour les Categories).
"""

from collections.abc import Sequence

from sqlalchemy.exc import IntegrityError

from src.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from src.modules.categories.models import Category
from src.modules.categories.repository import CategoryRepository
from src.modules.categories.schemas import CategoryCreate, CategoryUpdate
from src.modules.users.models import User


class CategoryService:
    def __init__(self, repository: CategoryRepository) -> None:
        self.repository = repository

    async def list_categories(
        self, skip: int = 0, limit: int = 100, name: str | None = None
    ) -> tuple[Sequence[Category], int]:
        """Récupère l'ensemble des catégories avec pagination."""
        categories = await self.repository.get_all(skip=skip, limit=limit, name=name)
        total = await self.repository.count(name=name)
        return (categories, total)

    async def get_category_or_404(self, entity_id: int) -> Category:
        """Récupère une catégorie ou lève une exception HTTP 404."""
        category = await self.repository.get_by_id(entity_id)
        if not category:
            raise NotFoundError(f"Catégorie avec l'ID {entity_id} introuvable.")
        return category

    async def create_category(self, created_by_id: int, data: CategoryCreate) -> Category:
        """Crée une nouvelle catégorie."""
        try:
            return await self.repository.create(created_by_id=created_by_id, data=data)
        except IntegrityError:
            raise ConflictError(f"Une catégorie avec le nom {data.name} existe déjà.") from None

    async def update_category(self, user: User, entity_id: int, data: CategoryUpdate) -> Category:
        """Met à jour une catégorie existante."""
        category = await self.get_category_or_404(entity_id)

        if not user.is_admin and category.created_by_id != user.id:
            raise ForbiddenError("Vous n'avez pas le droit de modifier cette catégorie.")

        try:
            return await self.repository.update(category, data)
        except IntegrityError:
            raise ConflictError(f"Une catégorie avec le nom {data.name} existe déjà.") from None

    async def delete_category(self, user: User, entity_id: int) -> None:
        """Supprime une categorie existante."""
        if not user.is_admin:
            raise ForbiddenError("Vous n'avez pas le droit de supprimer cette catégorie.")

        category = await self.get_category_or_404(entity_id)
        await self.repository.delete(category)
