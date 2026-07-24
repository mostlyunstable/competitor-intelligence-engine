"""Tests for the LLM response cache."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.infrastructure.cache import LLMResponseCache


class TestLLMResponseCache:
    @pytest.fixture
    def cache(self) -> LLMResponseCache:
        return LLMResponseCache()

    @pytest.mark.asyncio
    async def test_set_and_get_memory(self, cache: LLMResponseCache) -> None:
        response = {"summary": "test", "score": 0.9}
        await cache.set("test prompt", response)
        result = await cache.get("test prompt")
        assert result == response

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache: LLMResponseCache) -> None:
        result = await cache.get("nonexistent prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_invalidate(self, cache: LLMResponseCache) -> None:
        await cache.set("prompt", {"data": 1})
        await cache.invalidate("prompt")
        result = await cache.get("prompt")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear(self, cache: LLMResponseCache) -> None:
        await cache.set("p1", {"a": 1})
        await cache.set("p2", {"b": 2})
        count = await cache.clear()
        assert await cache.get("p1") is None
        assert await cache.get("p2") is None

    @pytest.mark.asyncio
    async def test_same_prompt_same_hash(self, cache: LLMResponseCache) -> None:
        await cache.set("identical", {"x": 1})
        result = await cache.get("identical")
        assert result == {"x": 1}

    @pytest.mark.asyncio
    async def test_different_prompts_different_keys(self, cache: LLMResponseCache) -> None:
        await cache.set("prompt A", {"a": 1})
        await cache.set("prompt B", {"b": 2})
        assert await cache.get("prompt A") == {"a": 1}
        assert await cache.get("prompt B") == {"b": 2}

    @pytest.mark.asyncio
    async def test_memory_expiry(self, cache: LLMResponseCache) -> None:
        """Test that in-memory entries expire after TTL."""
        # Manually insert with old timestamp
        key = cache._hash_prompt("old prompt")
        cache._memory_cache[key] = ({"data": "old"}, time.monotonic() - 7200)  # 2 hours ago

        with patch("app.ai.infrastructure.cache.get_settings") as mock_settings:
            mock_settings.return_value.cache.default_ttl_seconds = 3600
            result = await cache.get("old prompt")
        assert result is None

    def test_hash_deterministic(self, cache: LLMResponseCache) -> None:
        h1 = cache._hash_prompt("hello world")
        h2 = cache._hash_prompt("hello world")
        assert h1 == h2

    def test_hash_different_for_different_inputs(self, cache: LLMResponseCache) -> None:
        h1 = cache._hash_prompt("hello")
        h2 = cache._hash_prompt("world")
        assert h1 != h2
