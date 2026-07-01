#!/usr/bin/env python3
"""
Manual collection runner.

Usage:
    python scripts/collect.py --all
    python scripts/collect.py --competitor "HomeServe"
    python scripts/collect.py --id 1
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_env() -> None:
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


async def collect_all() -> None:
    from app.database.connection import db_manager
    from app.database.repositories.competitor_repository import CompetitorRepository
    from app.services.collection_service import collection_service

    await db_manager.connect()

    try:
        async with db_manager.session() as session:
            comp_repo = CompetitorRepository(session)
            competitors = await comp_repo.get_all()

            if not competitors:
                print("  No competitors found in database.")
                print("  Add competitors to competitors.json and restart the app.")
                return

            print(f"\n  Found {len(competitors)} competitor(s):")
            for comp in competitors:
                status = "enabled" if comp.enabled else "disabled"
                print(f"    [{comp.id}] {comp.name} ({status})")

            enabled = [c for c in competitors if c.enabled]
            if not enabled:
                print("\n  No enabled competitors to collect.")
                return

            print(f"\n  Collecting from {len(enabled)} enabled competitor(s)...\n")

            for comp in enabled:
                print(f"  Collecting: {comp.name} (ID: {comp.id})...")
                result = await collection_service.collect_competitor(comp.id)
                status = result.get("status", "unknown")
                elapsed = result.get("elapsed_seconds", 0)
                print(f"    Status: {status} ({elapsed}s)")
                if result.get("error"):
                    print(f"    Error: {result['error']}")
                print()

    finally:
        await collection_service.close()
        await db_manager.disconnect()


async def collect_by_name(name: str) -> None:
    from app.database.connection import db_manager
    from app.database.repositories.competitor_repository import CompetitorRepository
    from app.services.collection_service import collection_service

    await db_manager.connect()

    try:
        async with db_manager.session() as session:
            comp_repo = CompetitorRepository(session)
            competitor = await comp_repo.get_by_name(name)

            if not competitor:
                print(f"  Competitor '{name}' not found in database.")
                return

            print(f"\n  Collecting: {competitor.name} (ID: {competitor.id})...")
            result = await collection_service.collect_competitor(competitor.id)
            status = result.get("status", "unknown")
            elapsed = result.get("elapsed_seconds", 0)
            print(f"    Status: {status} ({elapsed}s)")
            if result.get("error"):
                print(f"    Error: {result['error']}")

    finally:
        await collection_service.close()
        await db_manager.disconnect()


async def collect_by_id(competitor_id: int) -> None:
    from app.database.connection import db_manager
    from app.database.repositories.competitor_repository import CompetitorRepository
    from app.services.collection_service import collection_service

    await db_manager.connect()

    try:
        async with db_manager.session() as session:
            comp_repo = CompetitorRepository(session)
            competitor = await comp_repo.get_by_id(competitor_id)

            if not competitor:
                print(f"  Competitor with ID {competitor_id} not found.")
                return

            print(f"\n  Collecting: {competitor.name} (ID: {competitor.id})...")
            result = await collection_service.collect_competitor(competitor.id)
            status = result.get("status", "unknown")
            elapsed = result.get("elapsed_seconds", 0)
            print(f"    Status: {status} ({elapsed}s)")
            if result.get("error"):
                print(f"    Error: {result['error']}")

    finally:
        await collection_service.close()
        await db_manager.disconnect()


def main() -> None:
    load_env()

    parser = argparse.ArgumentParser(
        description="Manual collection runner for Utservio Competitor Intelligence"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="Collect from all enabled competitors")
    group.add_argument("--competitor", type=str, help="Collect from a specific competitor by name")
    group.add_argument("--id", type=int, help="Collect from a specific competitor by ID")

    args = parser.parse_args()

    print("=" * 60)
    print("  Utservio Competitor Intelligence - Manual Collection")
    print("=" * 60)

    if args.all:
        asyncio.run(collect_all())
    elif args.competitor:
        asyncio.run(collect_by_name(args.competitor))
    elif args.id:
        asyncio.run(collect_by_id(args.id))


if __name__ == "__main__":
    main()
