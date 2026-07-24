import os
from typing import Any

import psutil
from fastapi import APIRouter

from app.ai.application.worker import _bg_tasks
from app.database.connection import db_manager

router = APIRouter()


@router.get("/metrics")
async def get_metrics() -> dict[str, Any]:
    # CPU & RAM of current process
    process = psutil.Process(os.getpid())
    cpu_percent = process.cpu_percent(interval=0.1)
    memory_info = process.memory_info()

    # DB Connection Pool
    pool_size, checkedin, checkedout = 0, 0, 0
    try:
        if db_manager._engine is not None:
            pool = db_manager._engine.pool
            pool_size = pool.size()  # type: ignore
            checkedin = pool.checkedin()  # type: ignore
            checkedout = pool.checkedout()  # type: ignore
    except Exception:
        pass

    # Worker Queue Depth
    queue_depth = len(_bg_tasks)

    return {
        "cpu_percent": cpu_percent,
        "ram_mb": memory_info.rss / 1024 / 1024,
        "db_pool_size": pool_size,
        "db_checkedin": checkedin,
        "db_checkedout": checkedout,
        "worker_queue_depth": queue_depth
    }
