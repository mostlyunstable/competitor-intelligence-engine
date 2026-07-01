from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import Base


class BaseRepository:
    def __init__(self, session: AsyncSession, model: type[Base]) -> None:
        self._session = session
        self._model = model

    async def get_by_id(self, record_id: int) -> Base | None:
        return await self._session.get(self._model, record_id)

    async def get_all(self, skip: int = 0, limit: int = 100) -> Sequence[Any]:
        stmt = select(self._model).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self._model)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create(self, **kwargs: Any) -> Any:
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def update(self, record_id: int, **kwargs: Any) -> Any | None:
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

    async def exists(self, record_id: int) -> bool:
        instance = await self.get_by_id(record_id)
        return instance is not None
