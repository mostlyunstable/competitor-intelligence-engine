#!/usr/bin/env python3
"""
Production startup script.

Starts the FastAPI application with uvicorn and the background scheduler.
"""

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


def main() -> None:
    load_env()

    host = os.environ.get("APP_HOST", "0.0.0.0")
    port = int(os.environ.get("APP_PORT", "8000"))
    workers = int(os.environ.get("WORKERS", "1"))
    log_level = os.environ.get("LOG_LEVEL", "info")

    print("=" * 60)
    print("  Utservio Competitor Intelligence Engine")
    print("=" * 60)
    print(f"  Host:         {host}")
    print(f"  Port:         {port}")
    print(f"  Workers:      {workers}")
    print(f"  Log Level:    {log_level}")
    print(f"  Debug:        {os.environ.get('CI_DEBUG', 'false')}")
    print(f"  Environment:  {os.environ.get('CI_ENVIRONMENT', 'production')}")
    print("=" * 60)
    print()

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level=log_level,
        access_log=True,
    )


if __name__ == "__main__":
    main()
