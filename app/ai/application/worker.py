"""Background AI worker: processes competitor analysis tasks asynchronously."""

import asyncio
import datetime
import json
import logging
import os
import traceback
from typing import Any

import structlog
from sqlalchemy import select

from app.ai.application.pipeline import AIPipeline
from app.ai.exceptions import PipelineError, ProviderError, ValidationError
from app.database.connection import db_manager
from app.database.models import CompetitorAIInsight

logger = structlog.get_logger("ai.worker")

# Concurrency control
_semaphore: asyncio.Semaphore | None = None
_bg_tasks: set[asyncio.Task[Any]] = set()

# DB fields the pipeline output maps to
_DB_FIELDS = {
    "summary", "key_differentiators", "market_position", "confidence_score",
    "data_quality_score", "pricing_analysis", "feature_gaps", "strategic_moves",
    "recommendations", "latest_updates",
}


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        from app.configuration.settings import get_settings
        max_concurrent = get_settings().llm.max_concurrent
        _semaphore = asyncio.Semaphore(max_concurrent)
    return _semaphore


class AIWorker:
    """
    Background worker that runs AI analysis for competitors.
    Uses semaphore for concurrency control and writes failures to DLQ.
    """

    def __init__(self) -> None:
        self._provider = None
        self._pipeline = None

    def _ensure_initialized(self) -> None:
        if self._provider is None:
            from app.ai.infrastructure.providers.openai_provider import OpenAIProvider
            self._provider = OpenAIProvider()
            self._pipeline = AIPipeline(self._provider)

    async def process_task(self, competitor_id: int, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Process a single AI analysis task with concurrency control.
        Returns the result dict on success, raises on failure.
        """
        self._ensure_initialized()
        sem = _get_semaphore()

        async with sem:
            logger.info("worker_task_start", competitor_id=competitor_id)
            # Update status to processing
            await self._update_status(competitor_id, "processing")

            try:
                result = await self._pipeline.run_analysis(competitor_id, raw_data)
                # Save to database
                await self._save_insight(competitor_id, result)
                # Update status to completed
                await self._update_status(competitor_id, "completed")
                logger.info("worker_task_complete", competitor_id=competitor_id)
                return result

            except (ValidationError, PipelineError) as e:
                logger.error("worker_task_validation_failed", competitor_id=competitor_id, error=str(e))
                await self._update_status(competitor_id, "failed")
                await self._write_dlq(competitor_id, raw_data, e)
                raise

            except ProviderError as e:
                logger.error("worker_task_provider_failed", competitor_id=competitor_id, error=str(e))
                await self._update_status(competitor_id, "failed")
                await self._write_dlq(competitor_id, raw_data, e)
                raise

            except Exception as e:
                logger.error("worker_task_unexpected_error", competitor_id=competitor_id, error=str(e))
                await self._update_status(competitor_id, "failed")
                await self._write_dlq(competitor_id, raw_data, e)
                raise

    async def _save_insight(self, competitor_id: int, insights: dict[str, Any]) -> None:
        """Upsert AI insight to the database."""
        db_data = {k: v for k, v in insights.items() if k in _DB_FIELDS}
        prompt_version = insights.get("prompt_version", "1.0.0")

        # Extract token usage for cost tracking
        token_usage = insights.get("_token_usage", {})
        prompt_tokens = token_usage.get("prompt_tokens", 0)
        completion_tokens = token_usage.get("completion_tokens", 0)
        total_tokens = token_usage.get("total_tokens", 0)
        # Rough cost estimate: $0.15/1M input, $0.60/1M output (NIM pricing)
        estimated_cost = (prompt_tokens * 0.15 + completion_tokens * 0.60) / 1_000_000

        async with db_manager.session() as session:
            stmt = select(CompetitorAIInsight).where(CompetitorAIInsight.competitor_id == competitor_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                for key, value in db_data.items():
                    setattr(existing, key, value)
                existing.prompt_version = prompt_version
                existing.prompt_tokens = prompt_tokens
                existing.completion_tokens = completion_tokens
                existing.total_tokens = total_tokens
                existing.estimated_cost_usd = estimated_cost
            else:
                new_insight = CompetitorAIInsight(
                    competitor_id=competitor_id,
                    llm_provider=self._provider.provider_name,
                    llm_model=self._provider.model_name,
                    prompt_version=prompt_version,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    estimated_cost_usd=estimated_cost,
                    **db_data,
                )
                session.add(new_insight)

            await session.commit()
            logger.info("insight_saved", competitor_id=competitor_id, cost_usd=round(estimated_cost, 6))

    async def _update_status(self, competitor_id: int, status: str) -> None:
        """Update processing_status in the database."""
        try:
            async with db_manager.session() as session:
                stmt = select(CompetitorAIInsight).where(CompetitorAIInsight.competitor_id == competitor_id)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()
                if existing:
                    existing.processing_status = status
                    await session.commit()
        except Exception as e:
            logger.warning("status_update_failed", competitor_id=competitor_id, error=str(e))

    async def _write_dlq(self, competitor_id: int, raw_data: dict[str, Any], error: Exception) -> None:
        """Write failed task to dead letter queue (async file I/O)."""
        try:
            from app.configuration.settings import get_settings
            dlq_path = os.path.join(os.getcwd(), "dlq", "ai_failures.jsonl")
            os.makedirs(os.path.dirname(dlq_path), exist_ok=True)

            entry = {
                "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
                "competitor_id": competitor_id,
                "error_type": type(error).__name__,
                "error": str(error),
                "traceback": traceback.format_exc(),
                "raw_data_keys": list(raw_data.keys()),
                "provider": self._provider.provider_name,
                "model": self._provider.model_name,
            }

            # Use asyncio to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._write_dlq_sync, dlq_path, entry)
            logger.info("dlq_write_complete", competitor_id=competitor_id, path=dlq_path)

        except Exception as e:
            logger.error("dlq_write_failed", competitor_id=competitor_id, error=str(e))

    @staticmethod
    def _write_dlq_sync(path: str, entry: dict) -> None:
        with open(path, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")


_worker_instance = AIWorker()


async def trigger_ai_analysis(competitor_id: int, raw_data: dict[str, Any]) -> None:
    """
    Fire-and-forget: spawn AI analysis as a background task.
    Non-blocking. Task runs independently of the caller.
    """
    from app.configuration.settings import get_settings
    if not get_settings().llm.enabled:
        logger.info("ai_disabled_skipping", competitor_id=competitor_id)
        return

    task = asyncio.create_task(_worker_instance.process_task(competitor_id, raw_data))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
    logger.info("ai_task_spawned", competitor_id=competitor_id)
