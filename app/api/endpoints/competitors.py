from fastapi import APIRouter, Depends, HTTPException, Security
from pydantic import BaseModel, Field, HttpUrl, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_api_key
from app.api.dependencies import get_session
from app.configuration.models import CollectionModule
from app.database.models import CollectionFrequency, Competitor
from app.database.repositories.competitor_repository import CompetitorRepository

router = APIRouter(prefix="/competitors", tags=["Competitors"])


class CompetitorCreate(BaseModel):
    """Create a new competitor for monitoring."""

    name: str = Field(..., min_length=1, max_length=255, description="Competitor name")
    website_url: HttpUrl = Field(..., description="Competitor website URL")

    @field_validator("website_url")
    @classmethod
    def validate_url(cls, v: Any) -> Any:
        import ipaddress
        import socket
        from urllib.parse import urlparse

        url = str(v)
        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only http and https URLs are allowed.")

        domain = parsed.hostname
        if not domain:
            raise ValueError("URL must have a valid hostname.")

        try:
            ip_str = socket.gethostbyname(domain)
            ip = ipaddress.ip_address(ip_str)
            if (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_multicast
            ):
                raise ValueError(
                    "Internal, reserved, or private IPs are forbidden (SSRF Protection)."
                )
        except ValueError:
            raise
        except socket.gaierror as err:
            raise ValueError(f"Could not resolve hostname: {domain}") from err

        return v

    enabled: bool = Field(True, description="Enable automatic collection")
    collection_frequency: CollectionFrequency = Field(
        CollectionFrequency.DAILY,
        description="How often to collect data",
    )
    modules: list[CollectionModule] = Field(
        default_factory=list,
        description="Specific modules to collect (empty = all)",
    )
    tags: list[str] = Field(default_factory=list, description="Tags for organization")
    notes: str | None = Field(None, description="Internal notes")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Example Corp",
                    "website_url": "https://example.com",
                    "enabled": True,
                    "collection_frequency": "daily",
                    "modules": ["services", "pricing", "content"],
                    "tags": ["technology", "saas"],
                    "notes": "Primary competitor in cloud space",
                }
            ]
        }
    }


class CompetitorUpdate(BaseModel):
    """Update an existing competitor."""

    name: str | None = Field(None, min_length=1, max_length=255)
    website_url: HttpUrl | None = None
    enabled: bool | None = None
    collection_frequency: CollectionFrequency | None = None
    modules: list[CollectionModule] | None = None
    tags: list[str] | None = None
    notes: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Updated Corp Name",
                    "collection_frequency": "weekly",
                    "enabled": False,
                }
            ]
        }
    }


class CompetitorResponse(BaseModel):
    """Competitor response with all fields."""

    id: int
    name: str
    website_url: str
    enabled: bool
    collection_frequency: str | None
    modules: list[str]
    tags: list[str]
    notes: str | None
    created_at: str | None
    updated_at: str | None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "name": "Example Corp",
                    "website_url": "https://example.com",
                    "enabled": True,
                    "collection_frequency": "daily",
                    "modules": ["services", "pricing", "content"],
                    "tags": ["technology", "saas"],
                    "notes": "Primary competitor in cloud space",
                    "created_at": "2026-07-09T10:00:00Z",
                    "updated_at": "2026-07-09T10:00:00Z",
                }
            ]
        }
    }


def _serialize_competitor(c: Competitor) -> CompetitorResponse:
    return CompetitorResponse(
        id=c.id,
        name=c.name,
        website_url=c.website_url,
        enabled=c.enabled,
        collection_frequency=c.collection_frequency.value if c.collection_frequency else None,
        modules=c.modules or [],
        tags=c.tags or [],
        notes=c.notes,
        created_at=c.created_at.isoformat() if c.created_at else None,
        updated_at=c.updated_at.isoformat() if c.updated_at else None,
    )


@router.get(
    "",
    response_model=list[CompetitorResponse],
    summary="List Competitors",
    description="Retrieve all registered competitors.",
    responses={
        200: {
            "description": "List of competitors",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "name": "Example Corp",
                            "website_url": "https://example.com",
                            "enabled": True,
                            "collection_frequency": "daily",
                            "modules": ["services", "pricing"],
                            "tags": ["technology"],
                            "notes": None,
                            "created_at": "2026-07-09T10:00:00Z",
                            "updated_at": "2026-07-09T10:00:00Z",
                        }
                    ]
                }
            },
        }
    },
)
async def list_competitors(
    session: AsyncSession = Depends(get_session),
    _auth: str = Security(verify_api_key),
) -> list[CompetitorResponse]:
    repo = CompetitorRepository(session)
    competitors = await repo.get_all()
    return [_serialize_competitor(c) for c in competitors]


@router.get(
    "/{competitor_id}",
    response_model=CompetitorResponse,
    summary="Get Competitor",
    description="Retrieve a specific competitor by ID.",
    responses={
        200: {
            "description": "Competitor details",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Example Corp",
                        "website_url": "https://example.com",
                        "enabled": True,
                        "collection_frequency": "daily",
                        "modules": ["services", "pricing"],
                        "tags": ["technology"],
                        "notes": None,
                        "created_at": "2026-07-09T10:00:00Z",
                        "updated_at": "2026-07-09T10:00:00Z",
                    }
                }
            },
        },
        404: {
            "description": "Competitor not found",
            "content": {"application/json": {"example": {"detail": "Competitor not found"}}},
        },
    },
)
async def get_competitor(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
    _auth: str = Security(verify_api_key),
) -> CompetitorResponse:
    repo = CompetitorRepository(session)
    competitor = await repo.get_by_id(competitor_id)
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return _serialize_competitor(competitor)


@router.post(
    "",
    response_model=CompetitorResponse,
    status_code=201,
    summary="Create Competitor",
    description="Register a new competitor for monitoring.",
    responses={
        201: {
            "description": "Competitor created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Example Corp",
                        "website_url": "https://example.com",
                        "enabled": True,
                        "collection_frequency": "daily",
                        "modules": ["services", "pricing"],
                        "tags": ["technology"],
                        "notes": "Primary competitor",
                        "created_at": "2026-07-09T10:00:00Z",
                        "updated_at": "2026-07-09T10:00:00Z",
                    }
                }
            },
        },
        409: {
            "description": "Competitor name already exists",
            "content": {
                "application/json": {"example": {"detail": "Competitor name already exists"}}
            },
        },
    },
)
async def create_competitor(
    data: CompetitorCreate,
    session: AsyncSession = Depends(get_session),
    _auth: str = Security(verify_api_key),
) -> CompetitorResponse:
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


@router.put(
    "/{competitor_id}",
    response_model=CompetitorResponse,
    summary="Update Competitor",
    description="Update an existing competitor's configuration.",
    responses={
        200: {
            "description": "Competitor updated",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "name": "Updated Corp",
                        "website_url": "https://example.com",
                        "enabled": True,
                        "collection_frequency": "weekly",
                        "modules": ["services", "pricing"],
                        "tags": ["technology"],
                        "notes": None,
                        "created_at": "2026-07-09T10:00:00Z",
                        "updated_at": "2026-07-09T11:00:00Z",
                    }
                }
            },
        },
        404: {
            "description": "Competitor not found",
            "content": {"application/json": {"example": {"detail": "Competitor not found"}}},
        },
    },
)
async def update_competitor(
    competitor_id: int,
    data: CompetitorUpdate,
    session: AsyncSession = Depends(get_session),
    _auth: str = Security(verify_api_key),
) -> CompetitorResponse:
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


@router.delete(
    "/{competitor_id}",
    status_code=204,
    summary="Delete Competitor",
    description="Remove a competitor and all associated data.",
    responses={
        204: {"description": "Competitor deleted"},
        404: {
            "description": "Competitor not found",
            "content": {"application/json": {"example": {"detail": "Competitor not found"}}},
        },
    },
)
async def delete_competitor(
    competitor_id: int,
    session: AsyncSession = Depends(get_session),
    _auth: str = Security(verify_api_key),
) -> None:
    repo = CompetitorRepository(session)
    deleted = await repo.delete(competitor_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Competitor not found")
