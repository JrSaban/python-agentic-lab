"""Routing & Controller Layer pour le domaine Maintenance."""

from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, status

from src.core.database import DbSessionDep, async_session_factory
from src.modules.auth.router import CurrentUserDep
from src.modules.categories.repository import CategoryRepository
from src.modules.jobs.models import Job
from src.modules.jobs.repository import JobRepository
from src.modules.jobs.schemas import JobSummaryResponse
from src.modules.jobs.service import JobService
from src.modules.maintenance.service import MaintenanceService
from src.modules.maintenance.tasks import prune_soft_deleted
from src.modules.todos.repository import TodoRepository

logger = structlog.get_logger()


router = APIRouter(prefix="/maintenance", tags=["Maintenance"])


# Factory de dépendance : instancie Repository et Service injectés par requête
def get_maintenance_service(
    session: DbSessionDep,
) -> MaintenanceService:
    todo_repository = TodoRepository(session)
    category_repository = CategoryRepository(session)
    job_service = JobService(JobRepository(session))
    return MaintenanceService(todo_repository, category_repository, job_service)


# Type alias pour injection propre et lisible (standard Python moderne)
MaintenanceServiceDep = Annotated[MaintenanceService, Depends(get_maintenance_service)]


async def _enqueue_prune(task_id: str) -> None:
    """Enqueue prune task."""
    try:
        await prune_soft_deleted.kicker().with_task_id(task_id).kiq()
    except Exception as exc:
        logger.exception("enqueue_prune_failed", task_id=task_id)
        async with async_session_factory() as session:
            job_service = JobService(JobRepository(session))
            await job_service.mark_finished(
                task_id=task_id, is_error=True, result=None, error=type(exc).__name__
            )
            await session.commit()


@router.post(
    "/prune",
    response_model=JobSummaryResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Lance une tâche de purge",
    description="Lance une tâche de purge.",
)
async def start_prune(
    service: MaintenanceServiceDep,
    current_user: CurrentUserDep,
    background_tasks: BackgroundTasks,
) -> Job:
    job = await service.start_prune(current_user=current_user)
    background_tasks.add_task(_enqueue_prune, job.task_id)
    return job
