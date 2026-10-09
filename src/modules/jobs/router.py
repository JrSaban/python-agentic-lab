"""Routing & Controller Layer pour le domaine Jobs."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from src.core.database import DbSessionDep
from src.core.schemas import LimitQuery, PaginatedResponse
from src.modules.auth.router import CurrentUserDep
from src.modules.jobs.models import JobStatus
from src.modules.jobs.repository import JobRepository
from src.modules.jobs.schemas import JobResponse, JobSummaryResponse
from src.modules.jobs.service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# Factory de dépendance : instancie Repository et Service injectés par requête
def get_job_service(
    session: DbSessionDep,
) -> JobService:
    repository = JobRepository(session)
    return JobService(repository)


# Type alias pour injection propre et lisible (standard Python moderne)
JobServiceDep = Annotated[JobService, Depends(get_job_service)]


@router.get(
    "",
    response_model=PaginatedResponse[JobSummaryResponse],
    summary="Lister tous les jobs",
    description="Retourne une liste paginée de jobs.",
)
async def list_jobs(
    service: JobServiceDep,
    current_user: CurrentUserDep,
    skip: Annotated[int, Query(ge=0, description="Nombre d'éléments à sauter")] = 0,
    limit: LimitQuery = 25,
    owner_id: Annotated[
        int | None, Query(description="Filtre sur le propriétaire (Seulement pour les admins)")
    ] = None,
    task_name: Annotated[
        str | None, Query(min_length=5, description="Filtre sur le nom de la tâche")
    ] = None,
    status: Annotated[
        JobStatus | None, Query(description="Filtre sur le statut de la tâche")
    ] = None,
) -> PaginatedResponse[JobSummaryResponse]:
    jobs, total = await service.list_jobs(
        current_user=current_user,
        skip=skip,
        limit=limit,
        owner_id=owner_id,
        task_name=task_name,
        status=status,
    )

    return PaginatedResponse(items=jobs, total=total, skip=skip, limit=limit)


@router.get(
    "/{task_id}",
    response_model=JobResponse,
    summary="Afficher un job",
    description="Récupère un job.",
)
async def get_job(
    service: JobServiceDep,
    current_user: CurrentUserDep,
    task_id: str,
) -> JobResponse:
    job = await service.get_job_or_404(current_user=current_user, task_id=task_id)

    return JobResponse.model_validate(job)
