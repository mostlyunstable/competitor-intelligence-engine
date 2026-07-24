import asyncio
import logging
from typing import Any

from sqlalchemy import select

from app.ai.application.pipeline import AIPipeline
from app.ai.infrastructure.providers.openai_provider import OpenAIProvider
from app.database.connection import db_manager
from app.database.models import CompetitorAIInsight

_bg_tasks: set[asyncio.Task[Any]] = set()

logger = logging.getLogger(__name__)


class AIWorker:
    """
    Background worker that listens for scraping completion events and triggers AI analysis.
    """

    def __init__(self) -> None:  
        self.provider = OpenAIProvider()
        self.pipeline = AIPipeline(self.provider)

    async def process_task(self, competitor_id: int, raw_data: dict[str, Any]) -> None:
        """
        Process an AI analysis task in the background.
        """
        logger.info(f"[AIWorker] Processing competitor_id={competitor_id}")

        try:
            from app.chaos import ChaosMonkey
            ChaosMonkey.maybe_crash_worker()

            # Generate insights
            insights = await self.pipeline.process_competitor(competitor_id, raw_data)

            # Save to database
            async with db_manager.session() as session:
                # Check if it already exists
                stmt = select(CompetitorAIInsight).where(CompetitorAIInsight.competitor_id == competitor_id)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    logger.info(f"[AIWorker] Updating existing insights for competitor_id={competitor_id}")
                    for key, value in insights.items():
                        setattr(existing, key, value)
                else:
                    logger.info(f"[AIWorker] Creating new insights for competitor_id={competitor_id}")
                    new_insight = CompetitorAIInsight(
                        competitor_id=competitor_id,
                        llm_provider="nvidia_nim",
                        llm_model=self.provider.settings.model_name,
                        **insights
                    )
                    session.add(new_insight)

                await session.commit()
                logger.info(f"[AIWorker] Task complete for competitor_id={competitor_id}")

        except Exception as e:
            logger.error(f"[AIWorker] Task failed for competitor_id={competitor_id}: {e!s}")
            # Write to DLQ
            try:
                from app.chaos import ChaosMonkey
                ChaosMonkey.maybe_fail_filesystem()
                import datetime
                import json
                import os
                os.makedirs("dlq", exist_ok=True)
                dlq_entry = {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "competitor_id": competitor_id,
                    "error": str(e),
                    "raw_data_keys": list(raw_data.keys())
                }
                with open("dlq/ai_failures.jsonl", "a") as f:
                    f.write(json.dumps(dlq_entry) + "\\n")
            except Exception as dlq_e:
                logger.error(f"[AIWorker] Failed to write to DLQ: {dlq_e}")


_worker_instance = AIWorker()

async def trigger_ai_analysis(competitor_id: int, raw_data: dict[str, Any]) -> None:
    """
    Fire-and-forget helper to spawn the AI task in the background without blocking the caller.
    """
    task = asyncio.create_task(_worker_instance.process_task(competitor_id, raw_data))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)
