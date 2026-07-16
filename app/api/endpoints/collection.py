from fastapi import APIRouter, BackgroundTasks, Security
from pydantic import BaseModel, Field

from app.api.auth import verify_api_key

router = APIRouter(prefix="/collection", tags=["Collection"])


class CollectRequest(BaseModel):
    competitor_id: int = Field(..., description="Competitor ID to collect data for")


class CollectResponse(BaseModel):
    status: str
    message: str
    competitor_id: int


@router.post(
    "/collect",
    response_model=CollectResponse,
    summary="Trigger Collection",
)
async def trigger_collection(
    request: CollectRequest,
    background_tasks: BackgroundTasks,
    _auth: str = Security(verify_api_key),
) -> CollectResponse:
    from app.services.collection_service import collection_service
    background_tasks.add_task(collection_service.collect_competitor, request.competitor_id)

    return CollectResponse(
        status="accepted",
        message="Collection job queued",
        competitor_id=request.competitor_id,
    )


@router.post(
    "/collect/{competitor_id}",
    response_model=CollectResponse,
    summary="Trigger Collection by ID",
)
async def trigger_collection_for_competitor(
    competitor_id: int,
    background_tasks: BackgroundTasks,
    _auth: str = Security(verify_api_key),
) -> CollectResponse:
    from app.services.collection_service import collection_service
    background_tasks.add_task(collection_service.collect_competitor, competitor_id)

    return CollectResponse(
        status="accepted",
        message="Collection job queued",
        competitor_id=competitor_id,
    )
