"""Service Layer (Logique métier pour les Jobs)."""

from collections.abc import Sequence
from datetime import UTC, datetime

import structlog

from src.core.exceptions import NotFoundError
from src.modules.jobs.models import Job, JobStatus
from src.modules.jobs.repository import JobRepository
from src.modules.jobs.schemas import JobCreate, JobUpdate
from src.modules.users.models import User

logger = structlog.get_logger()


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    async def list_jobs(
        self,
        current_user: User,
        skip: int = 0,
        limit: int = 25,
        owner_id: int | None = None,
        task_name: str | None = None,
        status: JobStatus | None = None,
    ) -> tuple[Sequence[Job], int]:
        """Fetch all jobs with pagination."""
        owner_id = current_user.id if not current_user.is_admin else owner_id

        jobs = await self.repository.get_all(
            skip=skip,
            limit=limit,
            owner_id=owner_id,
            task_name=task_name,
            status=status,
        )
        total = await self.repository.count(owner_id=owner_id, task_name=task_name, status=status)

        return (jobs, total)

    async def get_job_or_404(self, current_user: User, task_id: str) -> Job:
        """Get a job by its task ID or raise a 404 exception."""
        owner_id = current_user.id if not current_user.is_admin else None
        job = await self.repository.get_by_task_id(task_id=task_id, owner_id=owner_id)

        if not job:
            raise NotFoundError(f"Job avec l'ID {task_id} introuvable.")
        return job

    async def mark_running(self, *, task_id: str, task_name: str) -> Job:
        """Mark a job as running. If the job does not exist, it will be created."""
        job = await self.repository.get_by_task_id(task_id=task_id, owner_id=None)

        if job is None:
            create_data = JobCreate(
                task_id=task_id,
                task_name=task_name,
            )

            job = await self.repository.create(owner_id=None, data=create_data)

        update_data = JobUpdate(status=JobStatus.RUNNING, started_at=datetime.now(UTC))
        job = await self.repository.update(job, data=update_data)
        return job

    async def mark_finished(
        self, *, task_id: str, is_error: bool, result: dict | None, error: str | None
    ) -> Job | None:
        """Mark a job as finished."""
        job = await self.repository.get_by_task_id(task_id=task_id, owner_id=None)
        if job is None:
            logger.warning("job_not_tracked", task_id=task_id)
            return None

        update_data = JobUpdate(
            status=JobStatus.FAILED if is_error else JobStatus.SUCCEEDED,
            result=result,
            error=error,
            finished_at=datetime.now(UTC),
        )
        return await self.repository.update(job, data=update_data)
