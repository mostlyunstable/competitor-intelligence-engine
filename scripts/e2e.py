#!/usr/bin/env python3
"""End-to-end collection test runner.

Runs a full collection pipeline against a real competitor website using
a temporary SQLite database. Useful for validating the full pipeline
locally before running in production.

Usage:
    python scripts/e2e.py

Environment variables (optional):
    CI_DATABASE__URL        Override database URL (default: sqlite:///e2e.db)
    CI_LLM__ENABLED         Enable LLM fallback strategy (default: false)
    CI_LLM__API_KEY         API key for LLM provider (from environment)
    CI_LLM__PROVIDER        LLM provider name (default: nvidia)
    CI_WEBHOOK__ENABLED     Enable webhook alerts (default: false)
"""

import asyncio
import os

# Configure environment for local E2E run
os.environ.setdefault("CI_DATABASE__URL", "sqlite+aiosqlite:///e2e.db")
os.environ.setdefault("CI_LLM__ENABLED", "false")
os.environ.setdefault("CI_WEBHOOK__ENABLED", "false")

# Load API key from environment — never hardcode credentials here
llm_api_key = os.environ.get("CI_LLM__API_KEY", "")
if os.environ.get("CI_LLM__ENABLED", "false").lower() == "true" and not llm_api_key:
    print("WARNING: CI_LLM__ENABLED=true but CI_LLM__API_KEY is not set.")

from app.database.connection import db_manager  # noqa: E402
from app.services.collection_service import CollectionService  # noqa: E402


async def main() -> None:
    await db_manager.connect()
    await db_manager.drop_tables()
    await db_manager.create_tables()

    from app.database.models import Competitor

    async with db_manager.session() as session:
        comp = Competitor(
            name="Urban Company",
            website_url="https://urbancompany.com",
            modules=["company", "technographic", "pricing", "services"],
        )
        session.add(comp)
        await session.commit()
        await session.refresh(comp)
        comp_id = comp.id

    svc = CollectionService()
    await svc.collect_competitor(competitor_id=comp_id)
    await svc.close()
    print(f"E2E collection complete for competitor_id={comp_id}")


if __name__ == "__main__":
    asyncio.run(main())
