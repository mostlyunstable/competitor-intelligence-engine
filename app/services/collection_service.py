import time
from datetime import UTC, datetime
from typing import Any

import structlog

from app.collectors.company import CompanyCollector
from app.collectors.content import ContentCollector
from app.collectors.discovery import DiscoveryCollector
from app.collectors.pricing import PricingCollector
from app.collectors.service import ServiceCollector
from app.collectors.social import SocialCollector
from app.database.connection import db_manager
from app.database.repositories.collection_log_repository import CollectionLogRepository
from app.database.repositories.competitor_repository import CompetitorRepository
from app.database.repositories.competitor_source_repository import CompetitorSourceRepository

logger = structlog.get_logger(__name__)

MODULE_COLLECTORS: dict[str, Any] = {
    "discovery": DiscoveryCollector,
    "company": CompanyCollector,
    "services": ServiceCollector,
    "pricing": PricingCollector,
    "content": ContentCollector,
    "social": SocialCollector,
}

MODULE_URL_PATTERNS = {
    "company": ["", "/about", "/about-us", "/company"],
    "services": ["/services", "/our-services", "/what-we-do"],
    "pricing": ["/pricing", "/plans", "/cost"],
    "content": ["/blog", "/news", "/resources"],
    "social": ["", "/about"],
}


class CollectionService:
    def __init__(self) -> None:
        self._collectors: dict[str, Any] = {}

    def _get_collector(self, module: str) -> Any:
        if module not in self._collectors:
            collector_cls = MODULE_COLLECTORS.get(module)
            if collector_cls:
                self._collectors[module] = collector_cls()
        return self._collectors.get(module)

    async def collect_competitor(self, competitor_id: int) -> dict[str, Any]:
        start_time = time.time()
        log = logger.bind(competitor_id=competitor_id)

        try:
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

                base_url = getattr(competitor, "website_url", "")
                source_repo = CompetitorSourceRepository(session)
                log.info("collection_started", modules=modules)

                results: dict[str, Any] = {}
                errors: list[str] = []
                records_collected = 0

                for module in modules:
                    collector = self._get_collector(module)
                    if not collector:
                        log.warning("unknown_module", module=module)
                        continue

                    urls = self._get_urls_for_module(module, base_url, source_repo, competitor_id)

                    module_results = []
                    for url in urls:
                        try:
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

                log_repo = CollectionLogRepository(session)
                await log_repo.create(
                    competitor_id=competitor_id,
                    start_time=datetime.fromtimestamp(start_time, tz=UTC),
                    end_time=datetime.now(UTC),
                    success=len(errors) == 0,
                    duration_seconds=elapsed,
                    records_collected=records_collected,
                    errors=errors,
                    retry_count=0,
                )

                log.info("collection_completed", elapsed=elapsed, modules=modules)

                return {
                    "status": "success",
                    "competitor_id": competitor_id,
                    "modules_collected": modules,
                    "results": results,
                    "elapsed_seconds": elapsed,
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

    def _get_urls_for_module(
        self,
        module: str,
        base_url: str,
        source_repo: Any,
        competitor_id: int,
    ) -> list[str]:
        patterns = MODULE_URL_PATTERNS.get(module, [""])
        base = base_url.rstrip("/")
        return [f"{base}{pattern}" if pattern else base for pattern in patterns]

    async def close(self) -> None:
        for collector in self._collectors.values():
            if hasattr(collector, "close"):
                await collector.close()


collection_service = CollectionService()
