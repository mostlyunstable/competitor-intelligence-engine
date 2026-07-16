import os
from abc import ABC, abstractmethod
from typing import cast

import aiofiles


class StorageProvider(ABC):
    @abstractmethod
    async def save(self, content_hash: str, content: str | bytes, mime_type: str) -> str:
        """Saves content and returns the storage URI."""
        pass

    @abstractmethod
    async def load(self, uri: str) -> str | bytes:
        """Loads content from storage URI."""
        pass


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = base_dir
        self.raw_dir = os.path.join(self.base_dir, "raw_html")
        self.screenshot_dir = os.path.join(self.base_dir, "screenshots")

        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.screenshot_dir, exist_ok=True)

    async def save(self, content_hash: str, content: str | bytes, mime_type: str) -> str:
        if "html" in mime_type or "json" in mime_type:
            ext = ".html" if "html" in mime_type else ".json"
            directory = self.raw_dir
            mode = "w" if isinstance(content, str) else "wb"
        else:
            ext = ".png" if "image" in mime_type else ".bin"
            directory = self.screenshot_dir
            mode = "wb" if isinstance(content, bytes) else "w"

        filename = f"{content_hash}{ext}"
        filepath = os.path.join(directory, filename)

        async with aiofiles.open(filepath, mode) as f:
            await f.write(content)

        return f"file://{filepath}"

    async def load(self, uri: str) -> str | bytes:
        filepath = uri.replace("file://", "")
        mode = "rb" if filepath.endswith((".png", ".bin")) else "r"
        async with aiofiles.open(filepath, mode) as f:
            return cast("str | bytes", await f.read())


class S3CompatibleStorageProvider(StorageProvider):
    def __init__(self, bucket: str, endpoint: str | None = None):
        self.bucket = bucket
        self.endpoint = endpoint
        # Future MinIO / AWS S3 Support

    async def save(self, content_hash: str, content: str | bytes, mime_type: str) -> str:
        raise NotImplementedError("S3 storage not yet fully implemented")

    async def load(self, uri: str) -> str | bytes:
        raise NotImplementedError("S3 storage not yet fully implemented")


storage_provider = LocalStorageProvider()
