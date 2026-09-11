"""Configuration du logging de l'application."""

import logging

from src.core.config import settings


def setup_logging() -> None:
    """Configure le logger racine de l'application."""
    level = logging.DEBUG if settings.DEBUG else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
