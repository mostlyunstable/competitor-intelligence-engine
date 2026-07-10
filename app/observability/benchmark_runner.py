#!/usr/bin/env python3
"""Observability benchmark runner.

Runs the full collection pipeline against all configured competitors and
generates observability reports in the ``reports/`` directory.

Usage (from project root)::

    python -m app.observability.benchmark_runner

Or via the convenience script::

    python scripts/benchmark.py

Environment variables:
    CI_DATABASE__URL    Database URL (default: sqlite:///benchmark.db)
    COMPETITORS_JSON    Path to competitors config (default: competitors.json)
"""

from __future__ import annotations

import asyncio
import json
import os

import sqlalchemy as sa

from app.observability.metrics_exporter import MetricsExporter
from app.services.collection_service import CollectionService


async def main() -> None:
    print("==========================================")
    print("OBSERVABILITY BENCHMARK RUNNER")
    print("==========================================")

    from app.database.connection import db_manager

    os.environ.setdefault("CI_DATABASE__URL", "sqlite+aiosqlite:///benchmark.db")

    print("Initializing Benchmark DB...")
    await db_manager.connect()
    await db_manager.drop_tables()
    await db_manager.create_tables()

    competitors_path = os.environ.get("COMPETITORS_JSON", "competitors.json")
    with open(competitors_path) as f:
        data = json.load(f)
        competitors = data.get("competitors", [])

    if not competitors:
        print(f"No competitors found in {competitors_path}")
        return

    # Seed the DB
    async with db_manager.session() as session:
        from app.database.models import Competitor

        for c in competitors:
            comp = Competitor(
                name=c["name"],
                website_url=c["website_url"],
                modules=c.get(
                    "modules", ["discovery", "company", "services", "pricing", "content", "social"]
                ),
                enabled=True,
            )
            session.add(comp)
        await session.commit()

        result = await session.execute(sa.select(Competitor))
        comps = result.scalars().all()

    svc = CollectionService()

    for comp in comps:
        print("\n==========================================")
        print(f"Benchmarking: {comp.name}")
        print("==========================================")
        try:
            await svc.collect_competitor(competitor_id=comp.id)
            print(f"Completed {comp.name}")
        except Exception as e:
            print(f"Error collecting {comp.name}: {e}")

    await svc.close()

    print("\n==========================================")
    print("BENCHMARK COMPLETE. GENERATING OBSERVABILITY REPORTS...")
    print("==========================================")

    exporter = MetricsExporter(output_dir="reports")
    exporter.export_all()
    print("Reports written to reports/")


if __name__ == "__main__":
    asyncio.run(main())
