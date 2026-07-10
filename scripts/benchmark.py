#!/usr/bin/env python3
"""Convenience script to run the observability benchmark.

Usage:
    python scripts/benchmark.py

See app/observability/benchmark_runner.py for full documentation.
"""

import asyncio

from app.observability.benchmark_runner import main

if __name__ == "__main__":
    asyncio.run(main())
