"""Worker system for consuming queue messages and executing collections."""

import asyncio
import contextlib
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class CollectionWorker:
    """Background worker that consumes collection jobs from the queue."""

    def __init__(self, worker_id: str = "worker-1") -> None:
        self.worker_id = worker_id
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._processed = 0
        self._failed = 0

    async def start(self, queue: Any) -> None:
        if self._running:
            logger.warning("worker_already_running", worker_id=self.worker_id)
            return

        self._running = True
        self._queue = queue
        self._task = asyncio.create_task(self._run_loop())
        logger.info("worker_started", worker_id=self.worker_id)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info(
            "worker_stopped",
            worker_id=self.worker_id,
            processed=self._processed,
            failed=self._failed,
        )

    async def _run_loop(self) -> None:
        while self._running:
            try:
                processed = await self._queue.process_next()
                if processed:
                    self._processed += 1
                else:
                    await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._failed += 1
                logger.error(
                    "worker_error",
                    worker_id=self.worker_id,
                    error=str(e),
                )
                await asyncio.sleep(5)

    @property
    def stats(self) -> dict[str, Any]:
        return {
            "worker_id": self.worker_id,
            "running": self._running,
            "processed": self._processed,
            "failed": self._failed,
        }


class WorkerPool:
    """Manages multiple workers for horizontal scaling."""

    def __init__(self, num_workers: int = 1) -> None:
        self.workers: list[CollectionWorker] = [
            CollectionWorker(worker_id=f"worker-{i + 1}") for i in range(num_workers)
        ]
        self._queue: Any = None

    async def start(self, queue: Any) -> None:
        self._queue = queue
        for worker in self.workers:
            await worker.start(queue)
        logger.info("worker_pool_started", size=len(self.workers))

    async def stop(self) -> None:
        for worker in self.workers:
            await worker.stop()
        logger.info("worker_pool_stopped")

    def get_stats(self) -> list[dict[str, Any]]:
        return [w.stats for w in self.workers]


worker_pool = WorkerPool()
