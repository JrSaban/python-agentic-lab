"""Repository Pattern pour l'accès aux données de base."""

from collections.abc import Sequence
from typing import Literal, NamedTuple

from pydantic import BaseModel
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from src.core.database import Base


class FilterParams(NamedTuple):
    column: InstrumentedAttribute
    value: object
    op: Literal["eq", "ilike"]


class BaseRepository[ModelT: Base]:
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self.session = session
        self.model = model

    async def get_by_id(self, entity_id: int) -> ModelT | None:
        """Get model's entity by its ID"""
        query = select(self.model).where(self.model.id == entity_id)

        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update(self, entity: ModelT, data: BaseModel) -> ModelT:
        """Update an entity"""
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(entity, field, value)

        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)

        return entity

    async def delete(self, entity: ModelT) -> None:
        """Delete an entity"""
        await self.session.delete(entity)
        await self.session.flush()

    async def paginate(self, query: Select, skip: int, limit: int) -> Sequence[ModelT]:
        """Paginate a query"""
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_query(self, query: Select) -> int:
        """Count a query"""
        result = await self.session.execute(query)
        return result.scalar_one()

    def _apply_filter_params(self, query: Select, filters: list[FilterParams]) -> Select:
        """Apply filters to a query"""
        for filter_param in filters:
            if filter_param.value is None:
                continue

            match filter_param.op:
                case "eq":
                    query = query.where(filter_param.column == filter_param.value)
                case "ilike":
                    query = query.where(filter_param.column.ilike(f"%{filter_param.value}%"))
                case _:
                    raise ValueError(f"Unsupported operator: {filter_param.op}")
        return query
