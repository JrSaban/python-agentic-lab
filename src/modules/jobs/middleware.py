"""
Middleware Taskiq : suit chaque exécution de job dans la table `jobs`.
Équivalent conceptuel des écouteurs Queue::before() / Queue::after() dans Laravel.

Tourne dans le worker, pas dans l'API : il est enregistré sur le broker (src/core/broker.py),
jamais dans main.py. Une panne du suivi est loguée mais n'empêche jamais un job de tourner.
"""

import structlog
from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

from src.core.database import async_session_factory
from src.modules.jobs.repository import JobRepository
from src.modules.jobs.service import JobService

logger = structlog.get_logger()


class JobTrackingMiddleware(TaskiqMiddleware):
    """Record each job's state (running, then succeeded or failed) around its execution."""

    async def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        """Mark the job as running, creating its row for a scheduled run."""
        try:
            async with async_session_factory() as session:
                service = JobService(repository=JobRepository(session))
                await service.mark_running(
                    task_id=message.task_id,
                    task_name=message.task_name,
                )
                await session.commit()
        except Exception:
            logger.exception(
                "job_tracking_failed",
                task_id=message.task_id,
                task_name=message.task_name,
            )
        return message  # obligatoire, sinon le job ne s'exécute pas

    async def post_execute(self, message: TaskiqMessage, result: TaskiqResult) -> None:
        """Mark the job as succeeded or failed; only the exception's class name is stored."""
        try:
            async with async_session_factory() as session:
                service = JobService(repository=JobRepository(session))
                await service.mark_finished(
                    task_id=message.task_id,
                    is_error=result.is_err,
                    result=result.return_value if not result.is_err else None,
                    error=type(result.error).__name__ if result.is_err else None,
                )
                await session.commit()
        except Exception:
            logger.exception(
                "job_tracking_failed",
                task_id=message.task_id,
                task_name=message.task_name,
                is_error=result.is_err,
            )
