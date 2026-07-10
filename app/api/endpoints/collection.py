from fastapi import APIRouter, BackgroundTasks, Security
from pydantic import BaseModel, Field

from app.api.auth import verify_api_key
from app.services.collection_service import collection_service

router = APIRouter(prefix="/collection", tags=["Collection"])


class CollectRequest(BaseModel):
    """Request to trigger data collection for a competitor."""

    competitor_id: int = Field(..., description="Competitor ID to collect data for")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "competitor_id": 1,
                }
            ]
        }
    }


class CollectResponse(BaseModel):
    """Collection trigger response."""

    status: str
    message: str
    competitor_id: int

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "accepted",
                    "message": "Collection started in background",
                    "competitor_id": 1,
                }
            ]
        }
    }


@router.post(
    "/collect",
    response_model=CollectResponse,
    summary="Trigger Collection",
    description="""
Trigger data collection for a competitor in the background.

The collection process will:
1. Discover new pages on the competitor's website
2. Extract services, pricing, content, and social data
3. Store results in the database
4. Update collection logs

This is a non-blocking operation. Use the `/collection/status/{competitor_id}` endpoint to check progress.
    """,
    responses={
        202: {
            "description": "Collection started",
            "content": {
                "application/json": {
                    "example": {
                        "status": "accepted",
                        "message": "Collection started in background",
                        "competitor_id": 1,
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
async def trigger_collection(
    request: CollectRequest,
    background_tasks: BackgroundTasks,
    _auth: str = Security(verify_api_key),
) -> CollectResponse:
    background_tasks.add_task(collection_service.collect_competitor, request.competitor_id)
    return CollectResponse(
        status="accepted",
        message="Collection started in background",
        competitor_id=request.competitor_id,
    )


@router.post(
    "/collect/{competitor_id}",
    response_model=CollectResponse,
    summary="Trigger Collection by ID",
    description="Trigger data collection for a specific competitor by ID.",
    responses={
        202: {
            "description": "Collection started",
            "content": {
                "application/json": {
                    "example": {
                        "status": "accepted",
                        "message": "Collection started in background",
                        "competitor_id": 1,
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
async def trigger_collection_for_competitor(
    competitor_id: int,
    background_tasks: BackgroundTasks,
    _auth: str = Security(verify_api_key),
) -> CollectResponse:
    background_tasks.add_task(collection_service.collect_competitor, competitor_id)
    return CollectResponse(
        status="accepted",
        message="Collection started in background",
        competitor_id=competitor_id,
    )
