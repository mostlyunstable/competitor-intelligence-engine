import asyncio
from app.collectors.fetcher import HybridFetcher

async def main():
    fetcher = HybridFetcher()
    result = await fetcher.fetch("https://urbancompany.com/about")
    print(f"Status: {result.status_code}")
    print(f"Length: {len(result.html)}")
    print(f"Method: {result.method}")
    print("Content preview:")
    print(result.html[:500])
    await fetcher.close()

if __name__ == "__main__":
    asyncio.run(main())
