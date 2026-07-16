import asyncio
from app.services.collection_service import CollectionService
from app.database.connection import db_manager

async def main():
    await db_manager.connect()
    
    svc = CollectionService()
    print("Starting collection for competitor ID 6 (Urban Company)...")
    result = await svc.collect_competitor(4)
    
    print("\nCollection Result:")
    print(result)
    
    if result.get("status") == "success":
        print(f"Discovered URLs: {result.get('discovered_urls')}")
        print("Modules Results:")
        for k, v in result.get("results", {}).items():
            print(f"  {k}: {v}")
            
    await db_manager.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
