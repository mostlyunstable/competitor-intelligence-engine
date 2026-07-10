import asyncio
import io
import json
from pathlib import Path
from typing import Any, cast
from urllib.parse import urlparse

import imagehash
import structlog
from PIL import Image

logger = structlog.get_logger(__name__)


class VisualDiffService:
    """Service to track visual UX changes on competitor websites using perceptual hashing."""

    def __init__(self, storage_dir: str = "./storage/screenshots"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.hashes_file = self.storage_dir / "visual_hashes.json"
        self._lock = asyncio.Lock()

    def _get_filename(self, competitor_id: int, url: str) -> str:
        """Generate a safe filename/key for the hash."""
        parsed = urlparse(url)
        safe_path = parsed.path.replace("/", "_").strip("_") or "index"
        return f"c{competitor_id}_{safe_path}"

    async def _load_hashes(self) -> dict[str, str]:
        if not self.hashes_file.exists():
            return {}
        try:
            return cast(dict[str, str], json.loads(self.hashes_file.read_text()))
        except json.JSONDecodeError:
            return {}

    async def _save_hashes(self, hashes: dict[str, str]) -> None:
        self.hashes_file.write_text(json.dumps(hashes))

    async def detect_visual_change(self, competitor_id: int, url: str, page_object: Any) -> bool:
        """
        Take an in-memory screenshot of the Playwright page and compare its hash to the last crawl.
        Returns True if a significant visual change occurred.
        """
        try:
            file_key = self._get_filename(competitor_id, url)

            # Take full page screenshot directly into memory
            screenshot_bytes = await page_object.screenshot(full_page=True)

            # Calculate current hash in memory
            hash_current = imagehash.phash(Image.open(io.BytesIO(screenshot_bytes)))

            async with self._lock:
                hashes = await self._load_hashes()
                previous_hash_str = hashes.get(file_key)

                # Update stored hash
                hashes[file_key] = str(hash_current)
                await self._save_hashes(hashes)

            if not previous_hash_str:
                # First time seeing this page, no baseline to compare against
                return False

            # Compare perceptual hashes
            hash_previous = imagehash.hex_to_hash(previous_hash_str)
            difference = hash_current - hash_previous

            logger.debug("visual_diff_calculated", url=url, difference=difference)

            # If difference is greater than threshold, UX has changed
            return difference > 5

        except Exception as e:
            logger.error("visual_diff_failed", url=url, error=str(e))
            return False
