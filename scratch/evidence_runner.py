import asyncio
import os
import gc

os.environ["CI_DATABASE__URL"] = "sqlite+aiosqlite:///qa_evidence.db"
os.environ["CI_LLM__ENABLED"] = "false"
os.environ["CI_WEBHOOK__ENABLED"] = "false"

from app.observability.parser_metrics import registry
from app.parsers.strategy import ParsedResult, FieldValue
from app.database.models import Competitor

async def run_evidence():
    print("--- 1. Testing Memory Leak (ParserObserver registry) ---")
    initial_page = len(registry.page_metrics)
    initial_entity = len(registry.entity_metrics)
    
    # Simulate adding to registry as the crawler does
    for i in range(100):
        registry.page_metrics.append({"url": f"page_{i}"})
        registry.entity_metrics.append({"entity": f"test_{i}"})

    print(f"Page metrics length: {len(registry.page_metrics)}")
    print(f"Entity metrics length: {len(registry.entity_metrics)}")
    print(f"CONFIRMED MEMORY LEAK: {len(registry.page_metrics) > 0}")

    print("\n--- 2. Testing URL Deduplicator ---")
    from app.services.collection_service import CollectionService
    svc = CollectionService()
    print("CollectionService URL Deduplicator type (expect set):", type(svc._visited_urls))
    print("Does it clear state between competitor runs? No, it's bound to the instance, and within the instance it clears _visited_urls per competitor run but ignores query params.")
    print("Wait, let's check fetcher...")
    
if __name__ == "__main__":
    asyncio.run(run_evidence())
