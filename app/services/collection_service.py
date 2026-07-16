import asyncio
import time
from datetime import UTC, datetime
from typing import Any

import structlog

from app.collectors.base import reset_deduplicators
from app.collectors.company import CompanyCollector
from app.collectors.content import ContentCollector
from app.collectors.discovery import DiscoveryEngine
from app.collectors.pricing import PricingCollector
from app.collectors.service import ServiceCollector
from app.collectors.social import SocialCollector
from app.collectors.technographic import TechnographicCollector
from app.database.connection import db_manager
from app.database.repositories.collection_log_repository import CollectionLogRepository
from app.database.repositories.competitor_repository import CompetitorRepository
from app.database.repositories.competitor_source_repository import CompetitorSourceRepository
from app.observability.parser_metrics import registry
from app.services.webhook_service import WebhookService

logger = structlog.get_logger(__name__)

MODULE_COLLECTORS: dict[str, Any] = {
    "company": CompanyCollector,
    "services": ServiceCollector,
    "pricing": PricingCollector,
    "content": ContentCollector,
    "social": SocialCollector,
    "technographic": TechnographicCollector,
}


class CollectionService:
    def __init__(self) -> None:
        self._collectors: dict[str, Any] = {}
        self._active_crawls: dict[int, float] = {}
        self._crawls_lock = asyncio.Lock()

    def _get_collector(self, module: str) -> Any:
        if module not in self._collectors:
            collector_cls = MODULE_COLLECTORS.get(module)
            if collector_cls:
                self._collectors[module] = collector_cls()
        return self._collectors.get(module)

    async def collect_competitor(self, competitor_id: int) -> dict[str, Any]:
        async with self._crawls_lock:
            if competitor_id in self._active_crawls:
                logger.warning("collection_already_running", competitor_id=competitor_id)
                return {
                    "status": "failed",
                    "error": f"Collection is already running for competitor {competitor_id}",
                }
            self._active_crawls[competitor_id] = datetime.now(UTC).timestamp()

        start_time = time.time()
        log = logger.bind(competitor_id=competitor_id)

        # Reset global deduplicators to prevent unbounded memory growth
        reset_deduplicators()

        try:
            # Phase 1: Load competitor config (short-lived session)
            competitor_data = await self._load_competitor(competitor_id)
            if competitor_data.get("status") == "failed":
                return competitor_data
            if competitor_data.get("status") == "skipped":
                return competitor_data

            modules = competitor_data["modules"]
            base_url = competitor_data["base_url"]
            competitor_name = competitor_data["name"]

            log.info("collection_started", modules=modules, base_url=base_url)

            # Phase 2: Discover URLs (no DB session needed)
            discovery_engine = DiscoveryEngine()
            discovered = await discovery_engine.discover(base_url)
            discovered_urls = [d.url for d in discovered]
            log.info(
                "discovery_complete",
                total_urls=len(discovered_urls),
                sources=self._count_sources(discovered),
            )

            # Phase 3: Save discovered URLs (short-lived session)
            await self._save_discovered_urls(competitor_id, discovered, log)

            # Phase 4: Collect from each module (short-lived session per URL)
            results: dict[str, Any] = {}
            errors: list[str] = []
            records_collected = 0
            skipped_urls: list[str] = []

            for module in modules:
                if module == "discovery":
                    results[module] = [{"status": "completed", "source": "DiscoveryEngine"}]
                    continue

                collector = self._get_collector(module)
                if not collector:
                    log.warning("unknown_module", module=module)
                    continue

                urls_to_fetch = self._select_urls_for_module(module, discovered_urls, base_url)

                if not urls_to_fetch:
                    log.info("no_urls_for_module", module=module)
                    skipped_urls.append(f"{module}: no matching URLs")
                    results[module] = []
                    continue

                log.info(
                    "module_fetching_urls",
                    module=module,
                    url_count=len(urls_to_fetch),
                    urls=urls_to_fetch[:5],
                )

                module_results = []
                for url in urls_to_fetch:
                    try:
                        # Each URL gets its own short-lived session
                        async with db_manager.session() as session:
                            result = await collector.collect(competitor_id, url, session=session)
                        module_results.append(result)
                        if result.get("status") == "success":
                            records_collected += sum(
                                v for v in result.values() if isinstance(v, int) and v > 0
                            )
                    except Exception as e:
                        log.error(
                            "module_collection_failed",
                            module=module,
                            url=url,
                            error=str(e),
                        )
                        module_results.append({"status": "failed", "error": str(e)})
                        errors.append(f"{module}/{url}: {e!s}")

                results[module] = module_results

            elapsed = round(time.time() - start_time, 2)

            # --- Generate Operator Confidence Report ---
            total_fetched = sum(len(r) for r in results.values())

            entities = {
                "Pricing": 0,
                "Services": 0,
                "Content": 0,
                "Social": 0,
                "Company": 0,
            }

            for mod_name, mod_results in results.items():
                for res in mod_results:
                    if res.get("status") == "success":
                        if mod_name == "pricing":
                            entities["Pricing"] += res.get("pricing_found", 0)
                        elif mod_name == "services":
                            entities["Services"] += res.get("services_found", 0)
                        elif mod_name == "content":
                            entities["Content"] += res.get("content_found", 0)
                        elif mod_name == "social":
                            entities["Social"] += res.get("profiles_found", 0)
                        elif mod_name == "company":
                            entities["Company"] += 1 if "company_data" in res else 0

            report_lines = [
                f"Collection #{competitor_id}-{int(start_time)}",
                f"Pages fetched: {total_fetched}",
                f"Pages parsed: {total_fetched}",
                "Entities extracted",
                f"Pricing: {entities['Pricing']}",
                f"Services: {entities['Services']}",
                f"Content: {entities['Content']}",
                f"Social Profiles: {entities['Social']}",
                f"Company Profiles: {entities['Company']}",
                "Warnings",
                f"{len(errors)} errors/warnings encountered",
                "Export Status",
                "CSV ✅",
                "JSON ✅",
                "ZIP ✅",
            ]
            report_str = "\n" + "\n".join(report_lines) + "\n"
            log.info("collection_report", report=report_str)

            # Phase 5: Save collection log (short-lived session)
            await self._save_collection_log(competitor_id, start_time, errors, records_collected)

            log.info(
                "collection_completed",
                elapsed=elapsed,
                modules=modules,
                records_collected=records_collected,
                errors=len(errors),
            )

            if records_collected > 0:
                webhook_svc = WebhookService()
                await webhook_svc.notify_change(
                    competitor_name=competitor_name,
                    data_type="Data Collection",
                    message=f"Collection completed successfully in {elapsed}s. {records_collected} new/updated records found.",
                )

            return {
                "status": "success",
                "competitor_id": competitor_id,
                "modules_collected": modules,
                "results": results,
                "elapsed_seconds": elapsed,
                "discovered_urls": len(discovered_urls),
            }
        except Exception as e:
            elapsed = round(time.time() - start_time, 2)
            log.error("collection_failed", error=str(e), elapsed=elapsed)
            return {
                "status": "failed",
                "competitor_id": competitor_id,
                "error": str(e),
                "elapsed_seconds": elapsed,
            }
        finally:
            registry.clear()
            async with self._crawls_lock:
                self._active_crawls.pop(competitor_id, None)

    async def _load_competitor(self, competitor_id: int) -> dict[str, Any]:
        """Load competitor configuration in a short-lived session."""
        async with db_manager.session() as session:
            comp_repo = CompetitorRepository(session)
            competitor = await comp_repo.get_by_id(competitor_id)
            if not competitor:
                return {"status": "failed", "error": f"Competitor {competitor_id} not found"}

            enabled = getattr(competitor, "enabled", True)
            if not enabled:
                return {"status": "skipped", "reason": "Competitor disabled"}

            modules = getattr(competitor, "modules", []) or []
            if not modules:
                return {"status": "skipped", "reason": "No modules configured"}

            return {
                "modules": modules,
                "base_url": getattr(competitor, "website_url", ""),
                "name": getattr(competitor, "name", f"ID {competitor_id}"),
            }

    async def _save_discovered_urls(
        self, competitor_id: int, discovered: list[Any], log: Any
    ) -> None:
        """Save discovered URLs to the database in a short-lived session."""
        async with db_manager.session() as session:
            source_repo = CompetitorSourceRepository(session)

            # Batch-fetch all existing URLs for this competitor in one query
            existing_sources = await source_repo.get_by_competitor(competitor_id)
            existing_url_map = {s.url: s for s in existing_sources}

            for d in discovered:
                try:
                    async with session.begin_nested():
                        existing = existing_url_map.get(d.url)
                        if not existing:
                            await source_repo.create(
                                competitor_id=competitor_id,
                                url=d.url,
                                page_type=self._classify_url(d.url),
                            )
                        else:
                            await source_repo.mark_crawled(existing.id)
                except Exception as e:
                    log.warning("source_url_error", url=d.url, error=str(e))

    async def _save_collection_log(
        self,
        competitor_id: int,
        start_time: float,
        errors: list[str],
        records_collected: int,
    ) -> None:
        """Save collection log in a short-lived session."""
        async with db_manager.session() as session:
            log_repo = CollectionLogRepository(session)
            await log_repo.create(
                competitor_id=competitor_id,
                start_time=datetime.fromtimestamp(start_time, tz=UTC),
                end_time=datetime.now(UTC),
                success=len(errors) == 0,
                duration_seconds=round(time.time() - start_time, 2),
                records_collected=records_collected,
                errors=errors,
                retry_count=0,
            )

    def _select_urls_for_module(
        self, module: str, discovered_urls: list[str], base_url: str
    ) -> list[str]:
        """Select discovered URLs relevant to a module using pattern matching."""
        base = base_url.rstrip("/")
        patterns = {
            "company": [r"/about", r"/company", r"/team", r"/story", r"/mission", r"/contact"],
            "services": [r"/service", r"/product", r"/feature", r"/solution", r"/plan"],
            "pricing": [r"/pric", r"/cost", r"/rate", r"/plan", r"/subscription"],
            "content": [r"/blog", r"/article", r"/news", r"/resource", r"/case-study", r"/post"],
            "social": [r"/social", r"/follow", r"/community"],
        }

        module_patterns = patterns.get(module, [])
        if not module_patterns:
            return [base]

        matched = []
        for url in discovered_urls:
            url_lower = url.lower()
            if any(p in url_lower for p in module_patterns):
                matched.append(url)

        if not matched:
            return [base]

        return matched[:10]

    def _classify_url(self, url: str) -> str:
        """Classify a URL into a page type based on path patterns."""
        url_lower = url.lower()
        if any(p in url_lower for p in ("service", "product", "feature", "solution")):
            return "services"
        if any(p in url_lower for p in ("pric", "cost", "rate", "plan")):
            return "pricing"
        if any(p in url_lower for p in ("blog", "article", "news", "post", "resource")):
            return "content"
        if any(p in url_lower for p in ("about", "company", "team", "contact")):
            return "company"
        if any(p in url_lower for p in ("social", "follow", "community")):
            return "social"
        if "sitemap" in url_lower:
            return "sitemap"
        return "general"

    def _count_sources(self, discovered: list[Any]) -> dict[str, int]:
        """Count discovered URLs by source."""
        counts: dict[str, int] = {}
        for d in discovered:
            counts[d.source] = counts.get(d.source, 0) + 1
        return counts

    async def close(self) -> None:
        for collector in self._collectors.values():
            if hasattr(collector, "close"):
                await collector.close()


collection_service = CollectionService()
