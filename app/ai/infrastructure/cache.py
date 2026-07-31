"""LLM response cache: avoids redundant LLM calls for identical prompts."""

import hashlib
import json
import time
from typing import Any

import structlog

from app.configuration.settings import get_settings

logger = structlog.get_logger("ai.cache")


class LLMResponseCache:
    """
    In-memory LLM response cache with TTL.
    Falls back gracefully if Redis is unavailable.
    """

    def __init__(self) -> None:
        self._memory_cache: dict[str, tuple[Any, float]] = {}
        self._redis_client = None
        self._redis_attempted = False

    def _get_redis(self):
        if self._redis_attempted:
            return self._redis_client
        self._redis_attempted = True
        try:
            import redis.asyncio as aioredis
            settings = get_settings()
            url = settings.queue.redis_url
            self._redis_client = aioredis.from_url(url, decode_responses=True, socket_timeout=2)
            logger.info("redis_cache_connected", url=url)
        except Exception as e:
            logger.warning("redis_cache_fallback", error=str(e))
            self._redis_client = None
        return self._redis_client

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        return hashlib.sha256(prompt.encode()).hexdigest()[:32]

    async def get(self, prompt: str) -> dict[str, Any] | None:
        key = self._hash_prompt(prompt)

        # Try Redis first
        redis = self._get_redis()
        if redis:
            try:
                raw = await redis.get(f"ai_cache:{key}")
                if raw:
                    logger.debug("cache_hit_redis", key=key)
                    return json.loads(raw)
            except Exception as e:
                logger.warning("redis_get_failed", key=key, error=str(e))

        # Fallback to in-memory
        entry = self._memory_cache.get(key)
        if entry:
            value, ts = entry
            settings = get_settings()
            ttl = settings.cache.default_ttl_seconds
            if time.monotonic() - ts < ttl:
                logger.debug("cache_hit_memory", key=key)
                return value
            del self._memory_cache[key]

        return None

    async def set(self, prompt: str, response: dict[str, Any]) -> None:
        key = self._hash_prompt(prompt)

        # Try Redis
        redis = self._get_redis()
        if redis:
            try:
                settings = get_settings()
                ttl = settings.cache.default_ttl_seconds
                await redis.setex(f"ai_cache:{key}", ttl, json.dumps(response, default=str))
                logger.debug("cache_set_redis", key=key)
                return
            except Exception as e:
                logger.warning("redis_set_failed", key=key, error=str(e))

        # Fallback to in-memory
        self._memory_cache[key] = (response, time.monotonic())
        logger.debug("cache_set_memory", key=key)

    async def invalidate(self, prompt: str) -> None:
        key = self._hash_prompt(prompt)
        redis = self._get_redis()
        if redis:
            try:
                await redis.delete(f"ai_cache:{key}")
            except Exception as e:
                logger.warning("redis_delete_failed", key=key, error=str(e))
        self._memory_cache.pop(key, None)

    async def clear(self) -> int:
        self._memory_cache.clear()
        redis = self._get_redis()
        if redis:
            try:
                keys = []
                async for k in redis.scan_iter("ai_cache:*"):
                    keys.append(k)
                if keys:
                    await redis.delete(*keys)
                    return len(keys)
            except Exception as e:
                logger.warning("redis_clear_failed", error=str(e))
        return 0


# Singleton
llm_cache = LLMResponseCache()
