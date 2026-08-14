import asyncio
import contextlib
import random
from datetime import UTC, datetime
from typing import Any

import structlog

from app.configuration.settings import get_settings
from app.database.connection import db_manager
from app.database.models import CollectionFrequency, CollectionLog
from app.database.repositories.competitor_repository import CompetitorRepository
from app.services.collection_service import collection_service

logger = structlog.get_logger(__name__)


class CollectionScheduler:
    def __init__(self) -> None:
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._prediction_task: asyncio.Task[None] | None = None
        self._backtest_task: asyncio.Task[None] | None = None
        self._interval_seconds: int = 60
        self._paused: bool = False
        self._collections_since_last_prediction: int = 0
        self._backtest_interval_seconds: int = 604800  # Weekly

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

        # Auto-build knowledge graph and generate initial predictions
        self._prediction_task = asyncio.create_task(self._initial_setup())

        # Weekly backtest cron
        self._backtest_task = asyncio.create_task(self._backtest_loop())

        logger.info("scheduler_started", interval=self._interval_seconds)

    async def _initial_setup(self) -> None:
        """Run once on startup: build knowledge graph, generate predictions."""
        await asyncio.sleep(5)  # Wait for DB to be ready
        try:
            async with db_manager.session() as session:
                from app.services.knowledge_graph import knowledge_graph
                stats = await knowledge_graph.build_from_database(session)
                logger.info("knowledge_graph_built_on_startup", nodes=stats.get("nodes", 0), edges=stats.get("edges", 0))
        except Exception:
            logger.exception("knowledge_graph_build_failed")

        try:
            async with db_manager.session() as session:
                from app.services.predictions.growth import growth_forecaster
                from app.services.predictions.risks import risk_analyzer
                from app.services.predictions.recommendations import recommendation_engine
                from app.services.predictions.benchmarking import predictive_benchmarker
                from app.services.predictions.trends import trend_analyzer

                forecasts = await growth_forecaster.forecast_all(session)
                risks = await risk_analyzer.analyze_all(session)
                recs = await recommendation_engine.generate_all(session)
                benchmarks = await predictive_benchmarker.benchmark_all(session)
                trends = await trend_analyzer.get_all_trends(session)

                logger.info("initial_predictions_generated",
                    forecasts=len(forecasts), risks=len(risks),
                    recommendations=len(recs), benchmarks=len(benchmarks),
                    trends=len(trends.get("pricing_trends", []) + trends.get("service_trends", [])))
        except Exception:
            logger.exception("initial_prediction_generation_failed")

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._prediction_task:
            self._prediction_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._prediction_task
            self._prediction_task = None
        if self._backtest_task:
            self._backtest_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._backtest_task
            self._backtest_task = None
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
            await asyncio.sleep(self._interval_seconds + random.uniform(0, 0.1 * self._interval_seconds))

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
                await asyncio.wait_for(
                    collection_service.collect_competitor(comp_id), timeout=3600.0
                )
                self._collections_since_last_prediction += 1
            except TimeoutError:
                logger.error("scheduled_collection_timed_out", competitor_id=comp_id)
            except Exception:
                logger.exception(
                    "publish_collection_job_failed",
                    competitor_id=comp_id,
                )

        # After processing collections, regenerate predictions if enough collections happened
        if self._collections_since_last_prediction >= 3:
            await self._regenerate_predictions()

    async def _regenerate_predictions(self) -> None:
        """Regenerate predictions after several collections."""
        self._collections_since_last_prediction = 0
        try:
            async with db_manager.session() as session:
                from app.services.predictions.growth import growth_forecaster
                from app.services.predictions.risks import risk_analyzer
                from app.services.predictions.benchmarking import predictive_benchmarker

                await growth_forecaster.forecast_all(session)
                await risk_analyzer.analyze_all(session)
                await predictive_benchmarker.benchmark_all(session)

                # Rebuild knowledge graph with new data
                from app.services.knowledge_graph import knowledge_graph
                await knowledge_graph.build_from_database(session)

                logger.info("predictions_regenerated_after_collections")
        except Exception:
            logger.exception("prediction_regeneration_failed")

    async def _backtest_loop(self) -> None:
        """Weekly backtest: compare old predictions against actuals."""
        await asyncio.sleep(60)  # Initial delay after startup
        while self._running:
            try:
                await self._run_backtest()
            except Exception:
                logger.exception("backtest_failed")
            await asyncio.sleep(self._backtest_interval_seconds)

    async def _run_backtest(self) -> None:
        """Compare predictions older than 30 days against actual DB values."""
        from datetime import timedelta
        from sqlalchemy import select, func
        from app.database.models import (
            CompetitorPrediction, PredictionEvaluation, PredictionType,
            CompetitorService, CompetitorPricing,
        )

        async with db_manager.session() as session:
            cutoff = datetime.now(UTC) - timedelta(days=30)

            # Fetch predictions older than 30 days that haven't been evaluated
            stmt = (
                select(CompetitorPrediction)
                .where(CompetitorPrediction.predicted_at < cutoff)
                .order_by(CompetitorPrediction.predicted_at)
                .limit(100)
            )
            predictions = (await session.execute(stmt)).scalars().all()

            if not predictions:
                logger.info("backtest_no_predictions")
                return

            evaluations = 0
            total_mape = 0.0
            total_rmse = 0.0

            for pred in predictions:
                try:
                    actual_value = await self._get_actual_value(
                        session, pred.competitor_id, pred.prediction_type.value
                    )
                    if actual_value is None:
                        continue

                    predicted_value = 0.0
                    pred_data = pred.prediction_data or {}
                    if "overall_growth_score" in pred_data:
                        predicted_value = float(pred_data["overall_growth_score"])
                    elif "growth_score" in pred_data:
                        predicted_value = float(pred_data["growth_score"])
                    else:
                        continue

                    error = abs(predicted_value - actual_value)
                    mape = error / max(abs(actual_value), 1) * 100
                    rmse = error ** 2

                    evaluation = PredictionEvaluation(
                        competitor_id=pred.competitor_id,
                        prediction_type=pred.prediction_type.value,
                        predicted_value=predicted_value,
                        actual_value=actual_value,
                        error_margin=error,
                        confidence_score=pred.confidence_score,
                        model_used=pred.model_version,
                        evaluation_notes=f"Backtest: MAPE={mape:.1f}%, error={error:.3f}",
                    )
                    session.add(evaluation)

                    evaluations += 1
                    total_mape += mape
                    total_rmse += rmse

                except Exception as e:
                    logger.warning("backtest_eval_error", prediction_id=pred.id, error=str(e))
                    continue

            if evaluations > 0:
                avg_mape = total_mape / evaluations
                avg_rmse = (total_rmse / evaluations) ** 0.5
                await session.commit()
                logger.info(
                    "backtest_complete",
                    evaluations=evaluations,
                    avg_mape=round(avg_mape, 2),
                    avg_rmse=round(avg_rmse, 4),
                )
            else:
                logger.info("backtest_no_evaluations")

    async def _get_actual_value(
        self, session: Any, competitor_id: int, prediction_type: str
    ) -> float | None:
        """Get actual DB value for a prediction type to compare against."""
        from sqlalchemy import select, func
        from app.database.models import CompetitorService, CompetitorPricing, CompetitorContent

        if prediction_type == "growth":
            stmt = select(func.count()).select_from(CompetitorService).where(
                CompetitorService.competitor_id == competitor_id
            )
            return float((await session.execute(stmt)).scalar() or 0)
        elif prediction_type == "pricing":
            stmt = select(func.count()).select_from(CompetitorPricing).where(
                CompetitorPricing.competitor_id == competitor_id
            )
            return float((await session.execute(stmt)).scalar() or 0)
        elif prediction_type == "market_movement":
            stmt = select(func.count()).select_from(CompetitorContent).where(
                CompetitorContent.competitor_id == competitor_id
            )
            return float((await session.execute(stmt)).scalar() or 0)
        return None

    async def _get_last_collection_log(self, session: Any, competitor_id: int) -> Any:
        from app.database.repositories.collection_log_repository import CollectionLogRepository

        log_repo = CollectionLogRepository(session)
        return await log_repo.get_latest_by_competitor(competitor_id)

    def _should_collect(
        self, last_log: CollectionLog | None, frequency: CollectionFrequency, now: datetime
    ) -> bool:
        if not last_log or not last_log.start_time:
            return True

        if last_log.success is False:
            return True

        interval_map = {
            CollectionFrequency.HOURLY: 3600,
            CollectionFrequency.DAILY: 86400,
            CollectionFrequency.WEEKLY: 604800,
            CollectionFrequency.MONTHLY: 2592000,
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
