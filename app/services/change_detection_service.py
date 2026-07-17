from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import db_manager
from app.database.models import (
    ChangeLog,
    CompetitorContent,
    CompetitorPricing,
    CompetitorService,
    CompetitorSocial,
)

logger = structlog.get_logger(__name__)

DATA_MODELS = {
    "services": CompetitorService,
    "pricing": CompetitorPricing,
    "content": CompetitorContent,
    "social": CompetitorSocial,
}

COMPARE_FIELDS = {
    "services": ["service_name", "service_category", "description", "starting_price"],
    "pricing": ["service_name", "base_price", "promotional_price", "currency"],
    "content": ["title", "summary", "content_type"],
    "social": ["profile_url", "username"],
}


class ChangeDetectionService:
    """Detects changes between consecutive collections for a competitor."""

    async def detect_changes(
        self, competitor_id: int, data_type: str, session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Compare current data against previous snapshot and record changes."""
        model = DATA_MODELS.get(data_type)
        if not model:
            return []

        fields = COMPARE_FIELDS.get(data_type, [])
        changes: list[dict[str, Any]] = []

        # Get current records ordered by id
        current_stmt = select(model).where(model.competitor_id == competitor_id).order_by(model.id)
        current_records = (await session.execute(current_stmt)).scalars().all()

        if not current_records:
            return []

        # Get previous records (records collected before the most recent collected_at)
        if current_records:
            most_recent_time = max(r.collected_at for r in current_records if r.collected_at)
            prev_stmt = (
                select(model)
                .where(
                    model.competitor_id == competitor_id,
                    model.collected_at < most_recent_time,
                )
                .order_by(model.id)
            )
            prev_records = (await session.execute(prev_stmt)).scalars().all()
        else:
            prev_records = []

        # Index by content_hash for comparison
        current_by_hash = {r.content_hash: r for r in current_records if r.content_hash}
        prev_by_hash = {r.content_hash: r for r in prev_records if r.content_hash}

        # Detect added records
        for hash_val, record in current_by_hash.items():
            if hash_val not in prev_by_hash:
                change = {
                    "change_type": "added",
                    "data_type": data_type,
                    "record_id": record.id,
                    "new_value": self._record_to_dict(record, fields),
                }
                changes.append(change)
                await self._save_change(session, competitor_id, change)

        # Detect removed records
        for hash_val, record in prev_by_hash.items():
            if hash_val not in current_by_hash:
                change = {
                    "change_type": "removed",
                    "data_type": data_type,
                    "record_id": record.id,
                    "old_value": self._record_to_dict(record, fields),
                }
                changes.append(change)
                await self._save_change(session, competitor_id, change)

        # Detect modified records (same hash but different data)
        for hash_val in set(current_by_hash.keys()) & set(prev_by_hash.keys()):
            current_rec = current_by_hash[hash_val]
            prev_rec = prev_by_hash[hash_val]
            for field in fields:
                current_val = getattr(current_rec, field, None)
                prev_val = getattr(prev_rec, field, None)
                if current_val != prev_val:
                    change = {
                        "change_type": "modified",
                        "data_type": data_type,
                        "record_id": current_rec.id,
                        "old_value": {field: prev_val},
                        "new_value": {field: current_val},
                    }
                    changes.append(change)
                    await self._save_change(session, competitor_id, change)

        if changes:
            logger.info(
                "changes_detected",
                competitor_id=competitor_id,
                data_type=data_type,
                added=sum(1 for c in changes if c["change_type"] == "added"),
                removed=sum(1 for c in changes if c["change_type"] == "removed"),
                modified=sum(1 for c in changes if c["change_type"] == "modified"),
            )

        return changes

    def _record_to_dict(self, record: Any, fields: list[str]) -> dict[str, Any]:
        """Convert a model record to a dict of specified fields."""
        from decimal import Decimal

        result = {}
        for field in fields:
            val = getattr(record, field, None)
            if isinstance(val, Decimal):
                val = float(val)
            elif hasattr(val, "isoformat"):
                val = val.isoformat()
            elif hasattr(val, "value"):
                val = val.value
            result[field] = val
        return result

    async def _save_change(
        self, session: AsyncSession, competitor_id: int, change: dict[str, Any]
    ) -> None:
        """Persist a change log entry."""
        log_entry = ChangeLog(
            competitor_id=competitor_id,
            data_type=change["data_type"],
            change_type=change["change_type"],
            record_id=change.get("record_id"),
            old_value=change.get("old_value"),
            new_value=change.get("new_value"),
        )
        session.add(log_entry)

    async def get_recent_changes(
        self, competitor_id: int, limit: int = 50, session: AsyncSession | None = None
    ) -> list[dict[str, Any]]:
        """Get recent changes for a competitor."""
        async with db_manager.session() as sess:
            stmt = (
                select(ChangeLog)
                .where(ChangeLog.competitor_id == competitor_id)
                .order_by(ChangeLog.detected_at.desc())
                .limit(limit)
            )
            results = (await sess.execute(stmt)).scalars().all()
            return [
                {
                    "id": r.id,
                    "data_type": r.data_type,
                    "change_type": r.change_type,
                    "record_id": r.record_id,
                    "old_value": r.old_value,
                    "new_value": r.new_value,
                    "detected_at": r.detected_at.isoformat() if r.detected_at else None,
                }
                for r in results
            ]


change_detection_service = ChangeDetectionService()
