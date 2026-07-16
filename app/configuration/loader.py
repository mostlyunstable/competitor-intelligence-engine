import json
from pathlib import Path

import structlog

from app.configuration.models import CompetitorConfig, CompetitorsFile

logger = structlog.get_logger(__name__)


class ConfigurationLoader:
    def __init__(self, config_path: str | Path) -> None:
        self._config_path = Path(config_path)
        self._competitors: list[CompetitorConfig] = []

    def load(self) -> list[CompetitorConfig]:
        if not self._config_path.exists():
            logger.warning("competitors_config_not_found", path=str(self._config_path))
            return []

        try:
            raw = json.loads(self._config_path.read_text(encoding="utf-8"))
            parsed = CompetitorsFile(**raw)
            self._competitors = parsed.competitors
            logger.info(
                "competitors_config_loaded",
                count=len(self._competitors),
                path=str(self._config_path),
            )
            return self._competitors
        except Exception:
            logger.exception("failed_to_load_competitors_config", path=str(self._config_path))
            return []

    def reload(self) -> list[CompetitorConfig]:
        self._competitors.clear()
        return self.load()

    def get_competitors(self) -> list[CompetitorConfig]:
        return list(self._competitors)

    def get_competitor_by_name(self, name: str) -> CompetitorConfig | None:
        for c in self._competitors:
            if c.name.lower() == name.lower():
                return c
        return None
