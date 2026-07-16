from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import CollectionStatus, RawStorage
from app.database.repositories.base import BaseRepository


class RawStorageRepository(BaseRepository[RawStorage]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RawStorage)

    async def get_by_competitor(self, competitor_id: int) -> list[RawStorage]:
        stmt = (
            select(RawStorage)
            .where(RawStorage.competitor_id == competitor_id)
            .order_by(RawStorage.collected_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_url(self, competitor_id: int, source_url: str) -> RawStorage | None:
        stmt = select(RawStorage).where(
            RawStorage.competitor_id == competitor_id,
            RawStorage.source_url == source_url,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(
        self,
        competitor_id: int,
        source_url: str,
        content_hash: str,
        storage_uri: str | None = None,
        mime_type: str | None = None,
        file_size_bytes: int | None = None,
        metadata: dict[str, Any] | None = None,
        extracted_data: dict[str, Any] | None = None,
        collection_status: CollectionStatus = CollectionStatus.SUCCESS,
    ) -> RawStorage:
        """Insert or update raw storage based on URL.

        If an entry with the same URL exists, update its storage URI and metadata,
        and merge the extracted data.
        Otherwise, create a new record.
        """
        from sqlalchemy.exc import IntegrityError

        try:
            # We attempt to insert normally to rely on the DB's native constraint rather than checking first.
            record = await self.create(
                competitor_id=competitor_id,
                source_url=source_url,
                content_hash=content_hash,
                storage_uri=storage_uri,
                mime_type=mime_type,
                file_size_bytes=file_size_bytes,
                metadata_=metadata,
                extracted_data=extracted_data,
                collection_status=collection_status,
            )
            return record
        except IntegrityError:
            # A unique violation occurred (competitor_id, source_url).
            # Another concurrent transaction inserted the row first.
            # Rollback the failed insert in this session.
            await self._session.rollback()

            # Now that it definitely exists, retrieve it and update it safely.
            existing = await self.get_by_url(competitor_id, source_url)
            if existing:
                existing.storage_uri = storage_uri
                existing.mime_type = mime_type
                existing.file_size_bytes = file_size_bytes
                existing.metadata_ = metadata

                # Merge extracted_data to prevent modules from overwriting each other
                if existing.extracted_data and extracted_data:
                    merged = dict(existing.extracted_data)
                    for k, v in extracted_data.items():
                        merged[k] = v
                    existing.extracted_data = merged
                elif extracted_data:
                    existing.extracted_data = extracted_data

                existing.content_hash = content_hash
                existing.collection_status = collection_status
                existing.collected_at = datetime.now(UTC)
                await self._session.flush()
                return existing
            else:
                # Fallback if extremely weird concurrency things happen (deleted immediately after insert)
                raise RuntimeError(
                    "Failed to upsert RawStorage record due to concurrent deletion."
                ) from None

    async def delete_by_competitor(self, competitor_id: int) -> None:
        stmt = delete(RawStorage).where(RawStorage.competitor_id == competitor_id)
        await self._session.execute(stmt)
        await self._session.flush()

    async def get_latest(self, competitor_id: int) -> RawStorage | None:
        stmt = (
            select(RawStorage)
            .where(RawStorage.competitor_id == competitor_id)
            .order_by(RawStorage.collected_at.desc(), RawStorage.id.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
