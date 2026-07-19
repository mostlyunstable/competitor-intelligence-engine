import asyncio
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.database.models import SocialPlatform
from app.database.repositories.competitor_social_repository import CompetitorSocialRepository
from app.parsers.strategy_parser import StrategyParser
from app.utilities.content_hasher import compute_social_hash
from app.utilities.url_normalizer import normalize_url


class SocialCollector(BaseCollector):
    def __init__(self) -> None:
        super().__init__()
        self._parser = StrategyParser()

    async def collect(
        self, competitor_id: int, url: str, *, session: AsyncSession, **kwargs: Any
    ) -> dict[str, Any]:
        start_time: float = time.time()

        try:
            result = await self.fetch(url, competitor_id)
            if result.not_modified:
                return {
                    "status": "skipped",
                    "reason": "not_modified",
                    "profiles_found": 0,
                    "profiles_created": 0,
                    "profiles_updated": 0,
                    "elapsed_seconds": self._elapsed(start_time),
                }

            html = result.html

            if await self.is_unchanged(competitor_id, url, html, session):
                return {
                    "status": "skipped",
                    "reason": "unchanged",
                    "profiles_found": 0,
                    "profiles_created": 0,
                    "profiles_updated": 0,
                    "elapsed_seconds": self._elapsed(start_time),
                }

            parsed = await asyncio.to_thread(self._parser.parse_for_type, html, url, "social")
            await self.store_raw(competitor_id, url, html, session, extracted_data=parsed)
            profiles = parsed["social_profiles"]

            social_repo = CompetitorSocialRepository(session)
            profiles_created = 0
            profiles_updated = 0
            skipped_count = 0
            for profile in profiles:
                platform_str = (profile.get("platform") or "").strip().lower()
                try:
                    platform = SocialPlatform(platform_str)
                except ValueError:
                    skipped_count += 1
                    continue

                profile_url_raw = (profile.get("profile_url") or "").strip()
                if not profile_url_raw or not profile_url_raw.startswith(("http://", "https://")):
                    skipped_count += 1
                    continue
                profile_url = normalize_url(profile_url_raw, base_url=url)

                username = (profile.get("username") or "").strip() or None
                if username and len(username) > 255:
                    username = username[:255]

                content_hash = compute_social_hash(platform_str, profile_url, username)

                await social_repo.upsert(
                    competitor_id=competitor_id,
                    platform=platform,
                    profile_url=profile_url,
                    username=username,
                    content_hash=content_hash,
                )
                profiles_created += 1

            return {
                "status": "success",
                "profiles_found": len(profiles),
                "profiles_created": profiles_created,
                "profiles_updated": profiles_updated,
                "profiles_skipped": skipped_count,
                "elapsed_seconds": self._elapsed(start_time),
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "profiles_found": 0,
                "profiles_created": 0,
                "profiles_updated": 0,
                "elapsed_seconds": self._elapsed(start_time),
            }
