import asyncio
import os
import psutil
from app.observability.parser_metrics import registry, ParserObserver
from unittest.mock import MagicMock

def simulate_large_crawl():
    process = psutil.Process(os.getpid())
    mem_start = process.memory_info().rss / (1024 * 1024)
    print(f"Memory at start: {mem_start:.2f} MB")
    
    observer = ParserObserver()
    mock_result = MagicMock()
    mock_result.confidence = 0.9

    for i in range(100_000):
        observer.on_page_start(f"http://example.com/page{i}", 1, 1024, 100)
        
        # Simulate entities
        registry.entity_metrics.extend([{"id": j, "data": "A"*100} for j in range(10)])
        
        observer.on_page_end(mock_result)
        
        if i % 25_000 == 0 and i > 0:
            mem_current = process.memory_info().rss / (1024 * 1024)
            print(f"Memory at {i} pages: {mem_current:.2f} MB")

    mem_end = process.memory_info().rss / (1024 * 1024)
    print(f"Memory at end: {mem_end:.2f} MB")
    print(f"Total Memory Growth: {mem_end - mem_start:.2f} MB")
    
    if mem_end - mem_start > 50:
        print("FAIL: Memory leak confirmed (growth > 50MB)")
    else:
        print("PASS: Memory is stable")

if __name__ == "__main__":
    simulate_large_crawl()
