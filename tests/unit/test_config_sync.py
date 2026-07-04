import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.config_sync_service import ConfigSyncService


class TestConfigSyncService:
    def setup_method(self) -> None:
        self.service = ConfigSyncService()

    @pytest.mark.asyncio
    async def test_sync_competitors_from_config(self) -> None:
        config_data = {
            "competitors": [
                {
                    "name": "Test Corp",
                    "website_url": "https://test.com",
                    "enabled": True,
                    "collection_frequency": "daily",
                    "modules": ["discovery", "company"],
                    "tags": ["test"],
                    "notes": "Test competitor",
                }
            ]
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            self.service._loader = None

            with patch("app.services.config_sync_service.get_settings") as mock_settings:
                mock_settings.return_value.competitors_config_path = config_path

                with (
                    patch("app.services.config_sync_service.db_manager"),
                    patch("app.services.config_sync_service.CompetitorRepository") as mock_repo_cls,
                ):
                    mock_repo = AsyncMock()
                    mock_repo.get_by_name = AsyncMock(return_value=None)
                    mock_repo.create = AsyncMock()
                    mock_repo_cls.return_value = mock_repo

                    result = await self.service.sync_competitors()

                    assert result["status"] == "success"
                    assert result["synced"] == 1
                    mock_repo.create.assert_called_once()
        finally:
            Path(config_path).unlink()

    @pytest.mark.asyncio
    async def test_sync_updates_existing_competitors(self) -> None:
        config_data = {
            "competitors": [
                {
                    "name": "Existing Corp",
                    "website_url": "https://existing.com",
                    "enabled": True,
                    "collection_frequency": "daily",
                    "modules": ["company"],
                    "tags": ["tag1"],
                    "notes": "some notes",
                }
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name

        try:
            self.service._loader = None

            with patch("app.services.config_sync_service.get_settings") as mock_settings:
                mock_settings.return_value.competitors_config_path = config_path

                with (
                    patch("app.services.config_sync_service.db_manager"),
                    patch("app.services.config_sync_service.CompetitorRepository") as mock_repo_cls,
                ):
                    mock_repo = AsyncMock()
                    mock_repo.get_by_name = AsyncMock(return_value=MagicMock())
                    mock_repo_cls.return_value = mock_repo

                    result = await self.service.sync_competitors()

                    assert result["status"] == "success"
                    assert result["synced"] == 1
                    assert result["skipped"] == 0
                    mock_repo.update.assert_called_once()
                    mock_repo.create.assert_not_called()
        finally:
            Path(config_path).unlink()

    @pytest.mark.asyncio
    async def test_sync_with_no_config_file(self) -> None:
        self.service._loader = None

        with patch("app.services.config_sync_service.get_settings") as mock_settings:
            mock_settings.return_value.competitors_config_path = "/nonexistent/path.json"

            result = await self.service.sync_competitors()

            assert result["status"] == "no_config"
            assert result["synced"] == 0
