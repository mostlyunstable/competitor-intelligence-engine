from typing import Any

import structlog

from app.configuration.loader import ConfigurationLoader
from app.configuration.settings import get_settings
from app.database.connection import db_manager
from app.database.repositories.competitor_repository import CompetitorRepository

logger = structlog.get_logger(__name__)


class ConfigSyncService:
    def __init__(self) -> None:
        self._loader: ConfigurationLoader | None = None

    def _get_loader(self) -> ConfigurationLoader:
        if self._loader is None:
            settings = get_settings()
            self._loader = ConfigurationLoader(settings.competitors_config_path)
        return self._loader

    async def sync_competitors(self) -> dict[str, Any]:
        loader = self._get_loader()
        configs = loader.load()

        if not configs:
            return {"status": "no_config", "synced": 0, "skipped": 0}

        synced = 0
        skipped = 0

        try:
            async with db_manager.session() as session:
                comp_repo = CompetitorRepository(session)

                for config in configs:
                    existing = await comp_repo.get_by_name(config.name)
                    if existing:
                        await comp_repo.update(
                            existing.id,
                            website_url=config.website_url,
                            enabled=config.enabled,
                            collection_frequency=config.collection_frequency,
                            modules=[m.value for m in config.modules],
                            tags=config.tags,
                            notes=config.notes,
                        )
                        synced += 1
                        logger.info("competitor_updated", name=config.name)
                        continue

                    await comp_repo.create(
                        name=config.name,
                        website_url=config.website_url,
                        enabled=config.enabled,
                        collection_frequency=config.collection_frequency,
                        modules=[m.value for m in config.modules],
                        tags=config.tags,
                        notes=config.notes,
                    )
                    synced += 1
                    logger.info("competitor_synced", name=config.name)

                return {
                    "status": "success",
                    "synced": synced,
                    "skipped": skipped,
                    "total": len(configs),
                }
        except Exception as e:
            logger.exception("config_sync_failed")
            return {"status": "failed", "error": str(e), "synced": synced, "skipped": skipped}

    def reload_config(self) -> list[Any]:
        loader = self._get_loader()
        return loader.reload()


config_sync_service = ConfigSyncService()
