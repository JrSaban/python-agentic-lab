"""
Jobs du module maintenance, exécutés par le worker Taskiq.
Équivalent conceptuel d'une classe Job et de sa planification dans le scheduler de Laravel
($schedule->job(...)->weekly()).

Chaque job ouvre sa propre session et commit lui-même : le worker n'a ni FastAPI ni DbSessionDep.
"""

from src.core.broker import broker
from src.core.database import async_session_factory
from src.modules.categories.repository import CategoryRepository
from src.modules.jobs.repository import JobRepository
from src.modules.jobs.service import JobService
from src.modules.maintenance.service import MaintenanceService
from src.modules.todos.repository import TodoRepository


@broker.task(task_name="maintenance:prune_soft_deleted", schedule=[{"cron": "0 3 * * 0"}])
async def prune_soft_deleted() -> dict[str, int]:
    """Prune soft-deleted todos and categories."""
    async with async_session_factory() as session:
        maintenance_service = MaintenanceService(
            todo_repository=TodoRepository(session),
            category_repository=CategoryRepository(session),
            job_service=JobService(JobRepository(session)),
        )

        result = await maintenance_service.prune_soft_deleted()
        await session.commit()
    return result


@broker.task(task_name="maintenance:prune_old_jobs", schedule=[{"cron": "0 4 * * 0"}])
async def prune_old_jobs() -> dict[str, int]:
    """Prune old jobs."""
    async with async_session_factory() as session:
        maintenance_service = MaintenanceService(
            todo_repository=TodoRepository(session),
            category_repository=CategoryRepository(session),
            job_service=JobService(JobRepository(session)),
        )

        result = await maintenance_service.prune_old_jobs()
        await session.commit()
    return result
