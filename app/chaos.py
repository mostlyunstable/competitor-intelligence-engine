import asyncio
import os
import random
from collections.abc import Callable
from typing import Any

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)

class ChaosMonkey:
    """
    Simulates systemic failures across the application when CHAOS_MODE=1 is set.
    """

    @staticmethod
    def is_active() -> bool:
        return os.getenv("CHAOS_MODE") == "1"

    @classmethod
    async def maybe_fail_db(cls) -> None:
        if not cls.is_active():
            return
        if os.getenv("CHAOS_DB_DISCONNECT") == "1" and random.random() < 0.3:
            logger.warning("CHAOS: Simulating PostgreSQL connection failure.")
            raise ConnectionError("ChaosMonkey: PostgreSQL connection dropped randomly")

    @classmethod
    async def maybe_fail_network(cls) -> None:
        if not cls.is_active():
            return
        if os.getenv("CHAOS_NETWORK_TIMEOUT") == "1" and random.random() < 0.3:
            logger.warning("CHAOS: Simulating network timeout.")
            await asyncio.sleep(10)
            import httpx
            raise httpx.ReadTimeout("ChaosMonkey: Simulated network timeout")
        if os.getenv("CHAOS_DNS_FAILURE") == "1" and random.random() < 0.2:
            logger.warning("CHAOS: Simulating DNS resolution failure.")
            import httpx
            raise httpx.ConnectError("ChaosMonkey: Simulated DNS failure")

    @classmethod
    async def maybe_fail_openai(cls) -> None:
        if not cls.is_active():
            return
        import httpx
        from openai import APIConnectionError, APIStatusError, RateLimitError

        rand = random.random()
        if os.getenv("CHAOS_OPENAI_429") == "1" and rand < 0.2:
            logger.warning("CHAOS: Simulating OpenAI 429 Rate Limit.")
            raise RateLimitError("ChaosMonkey: Simulated 429 Rate Limit", response=httpx.Response(429, request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions")), body=None)
        if os.getenv("CHAOS_OPENAI_500") == "1" and rand >= 0.2 and rand < 0.4:
            logger.warning("CHAOS: Simulating OpenAI 500 Internal Error.")
            raise APIStatusError("ChaosMonkey: Simulated 500 Server Error", response=httpx.Response(500, request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions")), body=None)
        if os.getenv("CHAOS_OPENAI_TIMEOUT") == "1" and rand >= 0.4 and rand < 0.6:
            logger.warning("CHAOS: Simulating OpenAI API Timeout.")
            raise APIConnectionError(request=httpx.Request("POST", "https://api.openai.com/v1/chat/completions"))

    @classmethod
    def maybe_corrupt_ai_response(cls, response: str) -> str:
        if not cls.is_active():
            return response
        if os.getenv("CHAOS_AI_CORRUPTION") == "1" and random.random() < 0.4:
            logger.warning("CHAOS: Corrupting AI JSON response.")
            return "{" + response[:len(response)//2] + "INVALID_JSON..."
        return response

    @classmethod
    def maybe_fail_filesystem(cls) -> None:
        if not cls.is_active():
            return
        if os.getenv("CHAOS_FS_FULL") == "1" and random.random() < 0.3:
            logger.warning("CHAOS: Simulating Disk Full (ENOSPC).")
            raise OSError(28, "No space left on device")
        if os.getenv("CHAOS_FS_SLOW") == "1" and random.random() < 0.4:
            logger.warning("CHAOS: Simulating Slow Filesystem.")
            import time
            time.sleep(2)

    @classmethod
    def maybe_crash_worker(cls) -> None:
        if not cls.is_active():
            return
        if os.getenv("CHAOS_WORKER_CRASH") == "1" and random.random() < 0.1:
            logger.error("CHAOS: Simulating catastrophic worker crash.")
            os._exit(1)


class ChaosMonkeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable[[Request], Any]) -> Response:
        if not ChaosMonkey.is_active():
            return await call_next(request)  # type: ignore

        # Simulate partial HTTP responses or process termination midway
        if os.getenv("CHAOS_PROCESS_TERMINATION") == "1" and random.random() < 0.05:
            logger.error("CHAOS: Simulating process termination during request.")
            os._exit(1)

        return await call_next(request)  # type: ignore
