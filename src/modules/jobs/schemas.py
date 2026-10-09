"""
DTOs and Validation with Pydantic V2 for the Job domain.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from src.modules.jobs.models import JobStatus


class JobCreate(BaseModel):
    """Payload when creating a new job."""

    task_id: str
    task_name: str


class JobUpdate(BaseModel):
    """Payload when updating a job."""

    status: JobStatus | None = Field(default=None)
    result: JsonValue | None = Field(default=None)
    error: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    finished_at: datetime | None = Field(default=None)


class JobSummaryResponse(BaseModel):
    """Serialized payload for job summary"""

    task_id: str
    task_name: str
    status: JobStatus
    created_at: datetime
    finished_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class JobResponse(JobSummaryResponse):
    """Serialized payload for job detail"""

    owner_id: int | None
    result: JsonValue | None
    error: str | None
    started_at: datetime | None
    updated_at: datetime
