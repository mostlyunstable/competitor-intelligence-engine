from collections.abc import AsyncGenerator
from typing import Any

from app.database.connection import db_manager


async def get_session() -> AsyncGenerator[Any, None]:
    async with db_manager.session() as session:
        yield session
