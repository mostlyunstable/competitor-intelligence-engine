from collections.abc import Sequence
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import Base

T = TypeVar("T", bound=Base)


class BaseRepository[T: Base]:
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, record_id: int) -> T | None:
        return await self._session.get(self._model, record_id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[T]:
        stmt = select(self._model).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create(self, **kwargs: Any) -> T:
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def update(self, record_id: int, **kwargs: Any) -> T | None:
        instance = await self.get_by_id(record_id)
        if instance is None:
            return None

        updatable_fields = {
            f.name for f in self._model.__table__.columns if f.name not in ("id", "created_at")
        }
        for key, value in kwargs.items():
            if key in updatable_fields:
                setattr(instance, key, value)

        await self._session.flush()
        return instance

    async def delete(self, record_id: int) -> bool:
        instance = await self.get_by_id(record_id)
        if instance is None:
            return False
        await self._session.delete(instance)
        await self._session.flush()
        return True
