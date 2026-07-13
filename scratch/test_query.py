import asyncio
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import RawStorage

async def main():
    async with AsyncSessionLocal() as session:
        stmt = (
            select(RawStorage)
            .where(RawStorage.competitor_id == 6)
            .where(RawStorage.extracted_data.isnot(None))
            .order_by(RawStorage.collected_at.desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        raw = result.scalar_one_or_none()
        print(f"Raw: {raw}")
        if raw:
            print(f"Data: {raw.extracted_data}")

asyncio.run(main())
