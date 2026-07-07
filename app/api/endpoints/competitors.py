from enum import StrEnum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_api_key
from app.api.dependencies import get_session
from app.database.models import CollectionFrequency, Competitor
from app.database.repositories.competitor_repository import CompetitorRepository

router = APIRouter(prefix="/competitors", tags=["competitors"])


class CollectionModule(StrEnum):
    DISCOVERY = "discovery"
    COMPANY = "company"
    SERVICES = "services"
    PRICING = "pricing"
    CONTENT = "content"
    SOCIAL = "social"


class CompetitorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    website_url: HttpUrl
    enabled: bool = True
    collection_frequency: CollectionFrequency = CollectionFrequency.DAILY
    modules: list[CollectionModule] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class CompetitorUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    website_url: HttpUrl | None = None
    enabled: bool | None = None
    collection_frequency: CollectionFrequency | None = None
    modules: list[CollectionModule] | None = None
    tags: list[str] | None = None
    notes: str | None = None


def _serialize_competitor(c: Competitor) -> dict[str, Any]:
    return {
        "id": c.id,
        "name": c.name,
        "website_url": c.website_url,
        "enabled": c.enabled,
        "collection_frequency": c.collection_frequency.value if c.collection_frequency else None,
        "modules": c.modules or [],
        "tags": c.tags or [],
        "notes": c.notes,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("")
async def list_competitors(
    session: AsyncSession = Depends(get_session),
    _auth: str = Security(verify_api_key),
) -> list[dict[str, Any]]:
    repo = CompetitorRepository(session)
    competitors = await repo.get_all()
    return [_serialize_competitor(c) for c in competitors]


@router.get("/{competitor_id}")
async def get_competitor(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
    _auth: str = Security(verify_api_key),
) -> dict[str, Any]:
    repo = CompetitorRepository(session)
    competitor = await repo.get_by_id(competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return _serialize_competitor(competitor)


@router.post("", status_code=201)
async def create_competitor(
    data: CompetitorCreate,
    session: AsyncSession = Depends(get_session),
    _auth: str = Security(verify_api_key),
) -> dict[str, Any]:
    repo = CompetitorRepository(session)
    existing = await repo.get_by_name(data.name)
    if existing:
        raise HTTPException(status_code=409, detail="Competitor name already exists")
    competitor = await repo.create(
        name=data.name,
        website_url=str(data.website_url),
        enabled=data.enabled,
        collection_frequency=data.collection_frequency,
        modules=[m.value for m in data.modules],
        tags=data.tags,
        notes=data.notes,
    )
    return _serialize_competitor(competitor)


@router.put("/{competitor_id}")
async def update_competitor(
    competitor_id: int,
    data: CompetitorUpdate,
    session: AsyncSession = Depends(get_session),
    _auth: str = Security(verify_api_key),
) -> dict[str, Any]:
    repo = CompetitorRepository(session)
    update_data = data.model_dump(exclude_unset=True)
    if "website_url" in update_data:
        update_data["website_url"] = str(update_data["website_url"])
    if "modules" in update_data and update_data["modules"] is not None:
        update_data["modules"] = [m.value for m in update_data["modules"]]
    competitor = await repo.update(competitor_id, **update_data)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return _serialize_competitor(competitor)


@router.delete("/{competitor_id}", status_code=204)
async def delete_competitor(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
    _auth: str = Security(verify_api_key),
) -> None:
    repo = CompetitorRepository(session)
    deleted = await repo.delete(competitor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Competitor not found")
