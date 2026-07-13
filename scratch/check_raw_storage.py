import asyncio
from sqlalchemy import select
from app.database.session import AsyncSessionLocal
from app.database.models import RawStorage

async def check():
    async with AsyncSessionLocal() as session:
        stmt = select(RawStorage)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        for row in rows:
            print(f"ID: {row.id}, Competitor: {row.competitor_id}, Extracted Data Type: {type(row.extracted_data)}, Has Data: {bool(row.extracted_data)}")

asyncio.run(check())
