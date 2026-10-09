"""Service Layer (Logique métier pour maintenance)."""

from datetime import UTC, datetime, timedelta

from src.core.config import settings
from src.core.exceptions import ForbiddenError
from src.modules.categories.repository import CategoryRepository
from src.modules.jobs.models import Job
from src.modules.jobs.service import JobService
from src.modules.todos.repository import TodoRepository
from src.modules.users.models import User


class MaintenanceService:
    def __init__(
        self,
        todo_repository: TodoRepository,
        category_repository: CategoryRepository,
        job_service: JobService,
    ) -> None:
        self.todo_repository = todo_repository
        self.category_repository = category_repository
        self.job_service = job_service

    async def prune_soft_deleted(self) -> dict[str, int]:
        """Prune soft-deleted todos and categories."""
        before = datetime.now(UTC) - timedelta(days=settings.SOFT_DELETE_RETENTION_DAYS)

        todos_deleted_count = await self.todo_repository.prune_soft_deleted(before)
        categories_deleted_count = await self.category_repository.prune_soft_deleted(before)

        return {
            "todos": todos_deleted_count,
            "categories": categories_deleted_count,
        }

    async def start_prune(self, current_user: User) -> Job:
        """Create job to prune soft-deleted todos and categories."""
        if not current_user.is_admin:
            raise ForbiddenError("Vous devez être admin pour lancer le prune.")

        return await self.job_service.create_job(current_user.id, "maintenance:prune_soft_deleted")

    async def prune_old_jobs(self) -> dict[str, int]:
        """Prune old jobs."""
        before = datetime.now(UTC) - timedelta(days=settings.JOB_RETENTION_DAYS)
        jobs_deleted_count = await self.job_service.prune_old_jobs(before)

        return {
            "jobs": jobs_deleted_count,
        }
