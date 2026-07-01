from unittest.mock import patch

import pytest

from app.schedulers.scheduler import CollectionScheduler


class TestCollectionScheduler:
    def setup_method(self) -> None:
        self.scheduler = CollectionScheduler()

    def test_initial_state(self) -> None:
        assert self.scheduler.is_running is False
        assert self.scheduler._task is None

    @pytest.mark.asyncio
    async def test_start_creates_task(self) -> None:
        with (
            patch("app.schedulers.scheduler.get_settings") as mock_settings,
            patch("app.schedulers.scheduler.db_manager"),
            patch("app.schedulers.scheduler.CompetitorRepository"),
        ):
            mock_settings.return_value.scheduler.enabled = True
            mock_settings.return_value.scheduler.check_interval_seconds = 60

            await self.scheduler.start()
            assert self.scheduler.is_running is True
            assert self.scheduler._task is not None
            await self.scheduler.stop()

    @pytest.mark.asyncio
    async def test_start_when_disabled(self) -> None:
        with patch("app.schedulers.scheduler.get_settings") as mock_settings:
            mock_settings.return_value.scheduler.enabled = False

            await self.scheduler.start()
            assert self.scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_stop_cancels_task(self) -> None:
        with (
            patch("app.schedulers.scheduler.get_settings") as mock_settings,
            patch("app.schedulers.scheduler.db_manager"),
            patch("app.schedulers.scheduler.CompetitorRepository"),
        ):
            mock_settings.return_value.scheduler.enabled = True
            mock_settings.return_value.scheduler.check_interval_seconds = 60

            await self.scheduler.start()
            assert self.scheduler.is_running is True

            await self.scheduler.stop()
            assert self.scheduler.is_running is False
            assert self.scheduler._task is None

    @pytest.mark.asyncio
    async def test_start_when_already_running(self) -> None:
        with (
            patch("app.schedulers.scheduler.get_settings") as mock_settings,
            patch("app.schedulers.scheduler.db_manager"),
            patch("app.schedulers.scheduler.CompetitorRepository"),
        ):
            mock_settings.return_value.scheduler.enabled = True
            mock_settings.return_value.scheduler.check_interval_seconds = 60

            await self.scheduler.start()
            first_task = self.scheduler._task

            await self.scheduler.start()
            assert self.scheduler._task is first_task

            await self.scheduler.stop()
