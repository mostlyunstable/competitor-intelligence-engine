import asyncio
import contextlib
from datetime import UTC, datetime
from typing import Any

import structlog

from app.configuration.settings import get_settings
from app.database.connection import db_manager
from app.database.models import CollectionFrequency, CollectionLog
from app.database.repositories.competitor_repository import CompetitorRepository

logger = structlog.get_logger(__name__)


class CollectionScheduler:
    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._interval_seconds: int = 60
        self._paused: bool = False

    async def start(self) -> None:
        if self._running:
            logger.warning("scheduler_already_running")
            return

        settings = get_settings()
        if not settings.scheduler.enabled:
            logger.info("scheduler_disabled")
            return

        self._running = True
        self._paused = False
        self._interval_seconds = settings.scheduler.check_interval_seconds
        self._task = asyncio.create_task(self._run_loop())
        logger.info("scheduler_started", interval=self._interval_seconds)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        logger.info("scheduler_stopped")

    async def pause(self) -> None:
        self._paused = True
        logger.info("scheduler_paused")

    async def resume(self) -> None:
        self._paused = False
        logger.info("scheduler_resumed")

    async def _run_loop(self) -> None:
        while self._running:
            try:
                if not self._paused:
                    await self._check_and_publish()
            except Exception:
                logger.exception("scheduler_check_failed")
            await asyncio.sleep(self._interval_seconds)

    async def _check_and_publish(self) -> None:
        """Check for due competitors and publish collection jobs to the queue."""
        due_competitors: list[tuple[int, str, str]] = []
        try:
            async with db_manager.session() as session:
                comp_repo = CompetitorRepository(session)

                now = datetime.now(UTC)
                for freq in CollectionFrequency:
                    competitors = await comp_repo.get_by_frequency(freq.value)
                    for comp in competitors:
                        if not comp.enabled:
                            continue

                        last_log = await self._get_last_collection_log(session, comp.id)
                        if last_log and not self._should_collect(last_log, freq, now):
                            continue

                        due_competitors.append((comp.id, comp.name, freq.value))
        except Exception:
            logger.exception("scheduler_check_cycle_failed")
            return

        for comp_id, comp_name, freq_val in due_competitors:
            logger.info(
                "scheduling_collection",
                competitor_id=comp_id,
                name=comp_name,
                frequency=freq_val,
            )
            try:
                await self._publish_collection_job(comp_id)
            except Exception:
                logger.exception(
                    "publish_collection_job_failed",
                    competitor_id=comp_id,
                )

    async def _publish_collection_job(self, competitor_id: int) -> None:
        """Publish a collection job to the message queue."""
        from app.main import message_queue

        if message_queue is not None:
            from app.messagequeue.queue import MessageType

            await message_queue.publish(
                message_type=MessageType.COLLECTION,
                payload={"competitor_id": competitor_id},
                metadata={"source": "scheduler"},
            )
            logger.info("collection_job_published", competitor_id=competitor_id)
        else:
            from app.services.collection_service import collection_service

            logger.warning("queue_unavailable_executing_directly", competitor_id=competitor_id)
            await collection_service.collect_competitor(competitor_id)

    async def _get_last_collection_log(self, session: Any, competitor_id: int) -> Any:
        from app.database.repositories.collection_log_repository import CollectionLogRepository

        log_repo = CollectionLogRepository(session)
        return await log_repo.get_latest_by_competitor(competitor_id)

    def _should_collect(
        self, last_log: CollectionLog | None, frequency: CollectionFrequency, now: datetime
    ) -> bool:
        if not last_log or not last_log.start_time:
            return True

        interval_map = {
            CollectionFrequency.HOURLY: 3600,
            CollectionFrequency.DAILY: 86400,
            CollectionFrequency.WEEKLY: 604800,
        }
        interval = interval_map.get(frequency, 86400)
        start_time = last_log.start_time
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=UTC)
        elapsed = (now - start_time).total_seconds()
        return elapsed >= interval

    @property
    def is_running(self) -> bool:
        return self._running and not self._paused


scheduler = CollectionScheduler()
