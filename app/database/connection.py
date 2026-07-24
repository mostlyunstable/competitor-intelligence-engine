from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.configuration.settings import get_settings


class Base(DeclarativeBase):
    pass


class DatabaseManager:
    def __init__(self) -> None:
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def connect(self) -> None:
        settings = get_settings()
        self._engine = create_async_engine(
            settings.database.url,
            echo=settings.database.echo,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
            pool_recycle=settings.database.pool_recycle,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def disconnect(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._session_factory:
            raise RuntimeError("Database not connected. Call connect() first.")

        import tenacity
        from sqlalchemy.exc import DBAPIError, OperationalError

        from app.chaos import ChaosMonkey

        # Retry connection acquisition or commit errors on transient DB failures
        @tenacity.retry(
            retry=tenacity.retry_if_exception_type((OperationalError, DBAPIError, ConnectionError)),
            wait=tenacity.wait_exponential(multiplier=1, min=1, max=10),
            stop=tenacity.stop_after_attempt(5),
            reraise=True
        )
        async def _execute_with_retry() -> AsyncGenerator[AsyncSession, None]:
            await ChaosMonkey.maybe_fail_db()
            async with self._session_factory() as session: # type: ignore
                try:
                    yield session
                    await ChaosMonkey.maybe_fail_db()
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise

        # We must yield from the wrapped generator
        async for s in _execute_with_retry():
            yield s

    async def create_tables(self) -> None:
        if not self._engine:
            raise RuntimeError("Database not connected. Call connect() first.")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        if not self._engine:
            raise RuntimeError("Database not connected. Call connect() first.")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


db_manager = DatabaseManager()
