"""Schémas de pagination génériques"""

from typing import Annotated, Literal

from fastapi import Query
from pydantic import BaseModel, BeforeValidator


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    skip: int
    limit: int


LimitQuery = Annotated[
    Literal[10, 25, 50, 100],
    BeforeValidator(int),
    Query(description="Nombre max d'éléments"),
]
