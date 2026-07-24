from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import verify_any_auth
from app.api.dependencies import get_session
from app.database.models import Competitor, CompetitorAIInsight

router = APIRouter(
    prefix="/api/ai",
    tags=["AI Intelligence"],
    dependencies=[Depends(verify_any_auth)]
)

@router.get("/competitor/{competitor_id}")
async def get_competitor_insights(competitor_id: int, db: AsyncSession = Depends(get_session)) -> Any:
    """
    Retrieve the generated AI insights for a given competitor.
    """
    stmt = select(CompetitorAIInsight).where(CompetitorAIInsight.competitor_id == competitor_id)
    result = await db.execute(stmt)
    insight = result.scalar_one_or_none()

    if not insight:
        raise HTTPException(status_code=404, detail="AI insights not found for this competitor")

    return insight


@router.post("/analyze/{competitor_id}")
async def refresh_ai_analysis(
    competitor_id: int,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
) -> dict[str, Any]:
    """
    Manually trigger an AI analysis run for a competitor.
    """
    from app.ai.application.worker import trigger_ai_analysis

    stmt = select(Competitor).where(Competitor.id == competitor_id)
    result = await session.execute(stmt)
    competitor = result.scalar_one_or_none()

    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found")

    # In a real scenario we'd gather all the parsed data here.
    # For now we'll pass a placeholder or re-trigger collection.
    dummy_data = {"name": competitor.name, "url": competitor.website_url, "content": "Sample content to analyze"}

    await trigger_ai_analysis(competitor_id, dummy_data)

    return {"status": "Analysis triggered in the background"}


@router.get("/status")
async def get_ai_status() -> dict[str, str]:
    """
    Get overall AI pipeline status.
    """
    return {"status": "healthy", "provider": "nvidia_nim"}
