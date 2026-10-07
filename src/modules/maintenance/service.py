"""Service Layer (Logique métier pour maintenance)."""

from datetime import UTC, datetime, timedelta

from src.core.config import settings
from src.modules.categories.repository import CategoryRepository
from src.modules.todos.repository import TodoRepository


class MaintenanceService:
    def __init__(
        self, todo_repository: TodoRepository, category_repository: CategoryRepository
    ) -> None:
        self.todo_repository = todo_repository
        self.category_repository = category_repository

    async def prune_soft_deleted(self) -> dict[str, int]:
        """Prune soft-deleted todos and categories."""
        before = datetime.now(UTC) - timedelta(days=settings.SOFT_DELETE_RETENTION_DAYS)

        todos_deleted_count = await self.todo_repository.prune_soft_deleted(before)
        categories_deleted_count = await self.category_repository.prune_soft_deleted(before)

        return {
            "todos": todos_deleted_count,
            "categories": categories_deleted_count,
        }
