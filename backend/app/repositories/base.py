"""
Generic async repository base class.

Provides standard CRUD operations that concrete repositories inherit,
keeping DB access patterns consistent across the application.
"""

from __future__ import annotations

import uuid
from typing import Any, Generic, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async CRUD repository."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self._model = model
        self._session = session

    async def get_by_id(self, id: uuid.UUID | str) -> ModelType | None:
        """Fetch a single record by primary key."""
        if isinstance(id, str):
            try:
                id = uuid.UUID(id)
            except ValueError:
                pass
        return await self._session.get(self._model, id)

    async def get_all(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        order_by: str | None = None,
    ) -> Sequence[ModelType]:
        """Fetch paginated records."""
        stmt = select(self._model).offset(offset).limit(limit)
        if order_by and hasattr(self._model, order_by):
            stmt = stmt.order_by(getattr(self._model, order_by).desc())
        else:
            stmt = stmt.order_by(self._model.created_at.desc())
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        """Return total record count."""
        stmt = select(func.count()).select_from(self._model)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> ModelType:
        """Create and persist a new record."""
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def update(
        self, id: uuid.UUID | str, **kwargs: Any
    ) -> ModelType | None:
        """Update an existing record by ID."""
        if isinstance(id, str):
            try:
                id = uuid.UUID(id)
            except ValueError:
                pass
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key) and value is not None:
                setattr(instance, key, value)
        await self._session.flush()
        await self._session.refresh(instance)
        return instance

    async def delete(self, id: uuid.UUID | str) -> bool:
        """Delete a record by ID. Returns True if deleted."""
        if isinstance(id, str):
            try:
                id = uuid.UUID(id)
            except ValueError:
                pass
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True
