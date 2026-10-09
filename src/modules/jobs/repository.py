"""
Repository Pattern pour l'accès aux données de Job.
Encapsule les requêtes SQL (SQLAlchemy 2.0 select, add, delete).
"""

from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import CursorResult, Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.repository import BaseRepository, FilterParams
from src.modules.jobs.models import Job, JobStatus
from src.modules.jobs.schemas import JobCreate


class JobRepository(BaseRepository[Job]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Job)

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 25,
        owner_id: int | None = None,
        task_name: str | None = None,
        status: JobStatus | None = None,
    ) -> Sequence[Job]:
        """Get paginated jobs."""
        query = select(Job).order_by(Job.created_at.desc(), Job.id.desc())
        query = self._apply_filters(
            query,
            owner_id=owner_id,
            task_name=task_name,
            status=status,
        )

        return await self.paginate(query, skip, limit)

    async def get_by_task_id(self, *, task_id: str, owner_id: int | None) -> Job | None:
        """Get job by its task ID."""
        query = select(Job).where(Job.task_id == task_id)

        if owner_id is not None:
            query = query.where(Job.owner_id == owner_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def create(self, owner_id: int | None, data: JobCreate) -> Job:
        """Create and persist a new job."""
        job = Job(
            owner_id=owner_id,
            task_name=data.task_name,
            task_id=data.task_id,
        )
        self.session.add(job)
        # Génère l'ID via PostgreSQL sans commiter la transaction globale
        await self.session.flush()
        await self.session.refresh(job)
        return job

    async def prune_old_jobs(self, before: datetime) -> int:
        """Delete jobs older than the given date; return how many were deleted."""
        query = delete(Job).where(Job.created_at < before)
        result = await self.session.execute(query)
        return cast(CursorResult[Job], result).rowcount

    async def count(
        self,
        *,
        owner_id: int | None = None,
        task_name: str | None = None,
        status: JobStatus | None = None,
    ) -> int:
        """Count jobs with filters."""
        query = select(func.count()).select_from(Job)
        query = self._apply_filters(
            query,
            owner_id=owner_id,
            task_name=task_name,
            status=status,
        )

        return await self.count_query(query)

    def _apply_filters(
        self,
        query: Select,
        *,
        owner_id: int | None = None,
        task_name: str | None = None,
        status: JobStatus | None = None,
    ) -> Select:
        """Helper which applies filters on a query."""
        return self._apply_filter_params(
            query,
            [
                FilterParams(column=Job.owner_id, value=owner_id, op="eq"),
                FilterParams(column=Job.task_name, value=task_name, op="ilike"),
                FilterParams(column=Job.status, value=status, op="eq"),
            ],
        )
