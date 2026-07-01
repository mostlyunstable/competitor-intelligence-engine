from fastapi import APIRouter, BackgroundTasks, Security
from pydantic import BaseModel

from app.api.auth import verify_api_key
from app.services.collection_service import collection_service

router = APIRouter(prefix="/collection", tags=["collection"])


class CollectRequest(BaseModel):
    competitor_id: int


@router.post("/collect")
async def trigger_collection(
    request: CollectRequest,
    background_tasks: BackgroundTasks,
    _auth: str = Security(verify_api_key),
) -> dict[str, str]:
    background_tasks.add_task(collection_service.collect_competitor, request.competitor_id)
    return {"status": "accepted", "message": "Collection started in background"}


@router.post("/collect/{competitor_id}")
async def trigger_collection_for_competitor(
    competitor_id: int,
    background_tasks: BackgroundTasks,
    _auth: str = Security(verify_api_key),
) -> dict[str, str]:
    background_tasks.add_task(collection_service.collect_competitor, competitor_id)
    return {"status": "accepted", "message": "Collection started in background"}
