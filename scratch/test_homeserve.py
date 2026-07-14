import asyncio
import httpx
from app.database.connection import db_manager
from app.services.collection_service import collection_service
from app.database.models import Competitor
import os

async def main():
    await db_manager.connect()
    
    # 1. Fetch from DB
    async with db_manager.session() as session:
        from sqlalchemy import select
        result = await session.execute(select(Competitor).where(Competitor.website_url == "https://www.homeserve.com"))
        comp = result.scalar_one_or_none()
        
    if not comp:
        print("Competitor not found")
        return
        
    print(f"Collecting ID: {comp.id} - {comp.website_url}")
    result = await collection_service.collect_competitor(comp.id)
    
    print("\nResult:")
    print(result)

    await db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
