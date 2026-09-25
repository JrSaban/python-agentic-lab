"""Configuration du logging de l'application."""

import logging

import structlog

from src.core.config import settings


def setup_logging() -> None:
    """Configure structlog pour une sortie JSON structurée."""
    level = logging.DEBUG if settings.DEBUG else logging.WARNING

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
