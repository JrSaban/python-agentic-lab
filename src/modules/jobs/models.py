"""Modèles pour le domaine Jobs."""

from pydantic import JsonValue
from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, CheckConstraint, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from src.core.database import Base


class JobStatus(StrEnum):
    """Job's status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Job(Base):
    """Modèle SQLAlchemy pour la table 'jobs'."""

    __tablename__ = "jobs"

    task_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    task_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[JobStatus] = mapped_column(
        Enum(
            JobStatus,
            native_enum=False,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            length=20,
            create_constraint=False,
        ),
        default=JobStatus.PENDING,
        nullable=False,
    )
    result: Mapped[JsonValue | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps automatiques (created_at / updated_at) gérés côté base de données
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ({', '.join(f"'{status.value}'" for status in JobStatus)})",
            name="jobstatus",
        ),
    )

    def __repr__(self) -> str:
        return f"<Job task_id={self.task_id} task_name={self.task_name!r} status={self.status!r}>"
