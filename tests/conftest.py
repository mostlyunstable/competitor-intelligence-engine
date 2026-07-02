import os
from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database.connection import Base

TEST_DATABASE_URL = os.environ.get(
    "CI_TEST_DATABASE_URL",
    "postgresql+asyncpg://utservio_test:test_password@localhost:5433/utservio_ci_test",
)

_tables_created = False


@pytest_asyncio.fixture
async def engine():
    global _tables_created

    eng = create_async_engine(TEST_DATABASE_URL, echo=False)

    if not _tables_created:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        _tables_created = True

    yield eng

    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
