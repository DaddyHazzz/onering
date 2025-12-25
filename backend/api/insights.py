"""
Phase 8.7: Insights API

REST endpoints for draft insights, recommendations, and alerts.
All endpoints are read-only and collaborator-restricted.

Phase 8.7.1: Added optional 'now' query parameter for deterministic testing.
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Query
from typing import Annotated, Optional
from datetime import datetime
from backend.features.insights.service import InsightEngine
from backend.features.insights.models import DraftInsightsResponse
from backend.features.analytics.service import AnalyticsService
from backend.features.collaboration.service import get_draft
from backend.core.tracing import start_span

router = APIRouter(prefix="/api/insights", tags=["insights"])

# Dependency injection
def get_insight_engine() -> InsightEngine:
    """Get insight engine instance."""
    analytics_service = AnalyticsService()
    return InsightEngine(analytics_service)


@router.get("/drafts/{draft_id}", response_model=DraftInsightsResponse)
async def get_draft_insights(
    draft_id: str,
    user_id: Annotated[str, Header(alias="X-User-Id")],
    insight_engine: Annotated[InsightEngine, Depends(get_insight_engine)],
    now: Optional[str] = Query(None, description="Optional ISO timestamp for deterministic testing")
) -> DraftInsightsResponse:
    """
    Get insights, recommendations, and alerts for a draft.
    
    **Access:** Collaborators only (creator + invited collaborators)
    
    **Query Params:**
    - now (optional): ISO timestamp for deterministic testing (default: current time)
    
    **Returns:**
    - insights: List of derived insights (stalled, healthy, etc.)
    - recommendations: Actionable suggestions (pass_ring, invite_user)
    - alerts: Threshold-based warnings
    
    **Deterministic:** Same draft state + same 'now' always produces same insights.
    """
    with start_span("get_draft_insights", attributes={"draft_id": draft_id}):
        # Access control: Collaborators only
        try:
            draft = get_draft(draft_id)
        except Exception:
            raise HTTPException(status_code=404, detail="Draft not found")
        
        if not _is_collaborator(user_id, draft):
            raise HTTPException(
                status_code=403,
                detail="Only collaborators can view draft insights"
            )
        
        # Parse optional 'now' parameter for deterministic testing
        now_dt = None
        if now:
            try:
                now_dt = datetime.fromisoformat(now)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid 'now' timestamp format. Use ISO 8601.")
        
        # Compute insights
        try:
            insights_response = insight_engine.compute_draft_insights(draft_id, now=now_dt)
            return insights_response
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to compute insights: {str(e)}"
            )


def _is_collaborator(user_id: str, draft) -> bool:
    """
    Check if user is a collaborator (creator or in collaborators list).
    """
    creator_id = draft.creator_id
    collaborators = draft.collaborators
    
    return user_id == creator_id or user_id in collaborators

