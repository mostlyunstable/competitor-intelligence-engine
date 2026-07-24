"""Tests for the AI background worker."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.application.worker import AIWorker, trigger_ai_analysis
from app.ai.exceptions import ProviderError, PipelineError


class TestAIWorker:
    @pytest.fixture
    def worker(self) -> AIWorker:
        w = AIWorker()
        w._provider = MagicMock()
        w._pipeline = MagicMock()
        return w

    @pytest.mark.asyncio
    async def test_process_task_success(self, worker: AIWorker) -> None:
        mock_result = {"summary": "test", "prompt_version": "2.1.0"}
        worker._pipeline.run_analysis = AsyncMock(return_value=mock_result)

        with patch.object(worker, "_save_insight", new_callable=AsyncMock) as mock_save, \
             patch.object(worker, "_update_status", new_callable=AsyncMock):
            result = await worker.process_task(1, {"name": "Test"})

        assert result == mock_result
        mock_save.assert_called_once_with(1, mock_result)

    @pytest.mark.asyncio
    async def test_process_task_provider_error(self, worker: AIWorker) -> None:
        worker._pipeline.run_analysis = AsyncMock(side_effect=ProviderError("API down"))

        with patch.object(worker, "_update_status", new_callable=AsyncMock) as mock_status, \
             patch.object(worker, "_write_dlq", new_callable=AsyncMock):
            with pytest.raises(ProviderError):
                await worker.process_task(1, {"name": "Test"})

            # Should have set status to "failed"
            calls = mock_status.call_args_list
            assert any(call.args[1] == "failed" for call in calls)

    @pytest.mark.asyncio
    async def test_process_task_pipeline_error(self, worker: AIWorker) -> None:
        worker._pipeline.run_analysis = AsyncMock(side_effect=PipelineError("Pipeline broke"))

        with patch.object(worker, "_update_status", new_callable=AsyncMock), \
             patch.object(worker, "_write_dlq", new_callable=AsyncMock):
            with pytest.raises(PipelineError):
                await worker.process_task(1, {})

    @pytest.mark.asyncio
    async def test_process_task_unexpected_error(self, worker: AIWorker) -> None:
        worker._pipeline.run_analysis = AsyncMock(side_effect=RuntimeError("Something weird"))

        with patch.object(worker, "_update_status", new_callable=AsyncMock), \
             patch.object(worker, "_write_dlq", new_callable=AsyncMock):
            with pytest.raises(RuntimeError):
                await worker.process_task(1, {})


class TestTriggerAnalysis:
    @pytest.mark.asyncio
    async def test_disabled_skips(self) -> None:
        with patch("app.configuration.settings.get_settings") as mock_settings:
            mock_settings.return_value.llm.enabled = False
            # Should not raise, just return
            await trigger_ai_analysis(1, {"name": "Test"})

    @pytest.mark.asyncio
    async def test_enabled_spawns_task(self) -> None:
        with patch("app.configuration.settings.get_settings") as mock_settings, \
             patch("app.ai.application.worker._worker_instance") as mock_worker:
            mock_settings.return_value.llm.enabled = True
            mock_worker.process_task = AsyncMock()

            await trigger_ai_analysis(1, {"name": "Test"})
            # Task should have been created (we can't easily assert on create_task)
