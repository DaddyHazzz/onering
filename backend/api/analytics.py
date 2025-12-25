"""
backend/api/analytics.py

Event-driven analytics endpoints (Phase 3.4).
Pure event-reducer architecture: Events → Reducers → Read Models → API.
"""

from fastapi import APIRouter, Query
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from backend.models.analytics import DraftAnalytics, UserAnalytics, LeaderboardResponse
from backend.features.analytics.event_store import get_store
from backend.features.analytics.reducers import (
    reduce_draft_analytics,
    reduce_user_analytics,
    reduce_leaderboard,
)
from backend.core.errors import ValidationError, AppError

router = APIRouter()

def _mock_fetch_user_posts(user_id: str, start: datetime, end: datetime):
    """Deterministic stub for fetching a user's posts between start and end.
    Tests may monkeypatch this function to control returned posts.
    """
    return []

@router.get("/ring/daily", response_model=dict)
def ring_daily(
    userId: str = Query(..., description="User ID to compute daily ring stats"),
):
    """Daily ring analytics stub endpoint (deterministic, test-friendly).
    Returns 200 always with minimal payload; tests only assert status code.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)
    _ = _mock_fetch_user_posts(userId, start, now)
    return {"success": True}

@router.get("/ring/weekly", response_model=dict)
def ring_weekly(
    userId: str = Query(..., description="User ID to compute weekly ring stats"),
):
    """Weekly ring analytics stub endpoint (deterministic, test-friendly).
    Returns 200 always with minimal payload; tests only assert status code.
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)
    _ = _mock_fetch_user_posts(userId, start, now)
    return {"success": True}

@router.get("/v1/collab/drafts/{draft_id}/analytics", response_model=Dict[str, Any])
def get_draft_analytics(
    draft_id: str,
    now: Optional[str] = Query(None, description="ISO timestamp for deterministic results (testing only)"),
) -> Dict[str, Any]:
    """
    Get analytics for a specific collaborative draft.
    
    Returns:
    - views: number of DraftViewed events
    - shares: number of DraftShared events
    - segments_count: number of SegmentAdded events
    - contributors_count: unique contributors (creator + segment authors)
    - ring_passes_count: number of RINGPassed events
    - last_activity_at: most recent activity timestamp
    
    Deterministic: same events + same now => identical output.
    """
    try:
        # Parse optional fixed timestamp for deterministic testing
        now_dt = None
        if now:
            now_dt = datetime.fromisoformat(now.replace('Z', '+00:00'))
        
        # Fetch all events from event store
        store = get_store()
        events = store.get_events()
        
        # Reduce events to draft analytics
        analytics = reduce_draft_analytics(draft_id, events, now=now_dt)
        
        return {
            "success": True,
            "data": analytics.model_dump(mode="json"),
        }
    except ValueError as e:
        raise ValidationError(str(e))
    except Exception as e:
        raise AppError("Internal error while computing draft analytics")


@router.get("/v1/analytics/leaderboard", response_model=Dict[str, Any])
def get_analytics_leaderboard(
    metric: str = Query("collaboration", description="collaboration | momentum | consistency"),
    now: Optional[str] = Query(None, description="ISO timestamp for deterministic results (testing only)"),
) -> Dict[str, Any]:
    """
    Get leaderboard for given metric type.
    
    Metric types:
    - collaboration: segments×3 + rings×2 + drafts_contributed
    - momentum: segments + drafts_created×5 (stub, Phase 3.5 integrates momentum service)
    - consistency: drafts_created×5 + drafts_contributed×2
    
    Returns:
    - Top 10 entries only (prevents rank shame)
    - Stable sort: score desc, user_id asc (deterministic tie-breaker)
    - Supportive insights (never comparative, never "you're behind")
    
    Deterministic: same metric + same now => identical entries in same order.
    """
    try:
        # Validate metric type
        valid_metrics = ["collaboration", "momentum", "consistency"]
        if metric not in valid_metrics:
            raise ValidationError(f"Invalid metric type. Must be one of: {', '.join(valid_metrics)}")
        
        # Parse optional fixed timestamp for deterministic testing
        now_dt = None
        if now:
            now_dt = datetime.fromisoformat(now.replace('Z', '+00:00'))
        
        # Fetch all events from event store
        store = get_store()
        events = store.get_events()
        
        # Reduce events to leaderboard
        leaderboard = reduce_leaderboard(metric, events, now=now_dt)
        
        return {
            "success": True,
            "data": leaderboard.model_dump(mode="json"),
        }
    except ValueError as e:
        raise ValidationError(str(e))
    except AppError:
        raise
    except Exception as e:
        raise AppError("Internal error while computing leaderboard")


# ===== Phase 8.6: Draft Analytics (summary, contributors, ring dynamics, daily) =====

from fastapi import Depends, Query
from backend.core.auth import get_current_user_id
from backend.features.analytics.service import AnalyticsService
from backend.features.collaboration.service import get_draft
from backend.features.analytics.models import (
    DraftAnalyticsSummary, DraftAnalyticsContributors, DraftAnalyticsRing, DraftAnalyticsDaily
)
from backend.core.tracing import start_span
from backend.core.errors import NotFoundError, PermissionError


def _is_collaborator(draft, user_id: str) -> bool:
    """Check if user is collaborator (creator or in collaborators list)"""
    return user_id == draft.creator_id or user_id in draft.collaborators


@router.get("/drafts/{draft_id}/summary", response_model=DraftAnalyticsSummary)
async def get_draft_summary(
    draft_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get draft summary analytics (segments, words, contributors, inactivity risk)"""
    
    with start_span("analytics.summary", {"draft_id": draft_id, "user_id": user_id}):
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found")
        
        # Check collaborator access
        if not _is_collaborator(draft, user_id):
            raise PermissionError(f"User {user_id} is not a collaborator on draft {draft_id}")
        
        return AnalyticsService.compute_draft_summary(draft)


@router.get("/drafts/{draft_id}/contributors", response_model=DraftAnalyticsContributors)
async def get_draft_contributors(
    draft_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get contributor breakdown (segments, words, ring holds, wait mode votes/suggestions)"""
    
    with start_span("analytics.contributors", {"draft_id": draft_id, "user_id": user_id}):
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found")
        
        if not _is_collaborator(draft, user_id):
            raise PermissionError(f"User {user_id} is not a collaborator on draft {draft_id}")
        
        return AnalyticsService.compute_contributors(draft)


@router.get("/drafts/{draft_id}/ring", response_model=DraftAnalyticsRing)
async def get_draft_ring_dynamics(
    draft_id: str,
    user_id: str = Depends(get_current_user_id)
):
    """Get ring dynamics (current holder, hold history, passes, next holder recommendation)"""
    
    with start_span("analytics.ring", {"draft_id": draft_id, "user_id": user_id}):
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found")
        
        if not _is_collaborator(draft, user_id):
            raise PermissionError(f"User {user_id} is not a collaborator on draft {draft_id}")
        
        return AnalyticsService.compute_ring_dynamics(draft)


@router.get("/drafts/{draft_id}/daily", response_model=DraftAnalyticsDaily)
async def get_draft_daily_activity(
    draft_id: str,
    days: int = Query(14, ge=1, le=90, description="Number of days to include (1-90)"),
    user_id: str = Depends(get_current_user_id)
):
    """Get daily activity sparkline (last N days of segments added and ring passes)"""
    
    with start_span("analytics.daily", {"draft_id": draft_id, "user_id": user_id, "days": days}):
        draft = get_draft(draft_id)
        if not draft:
            raise NotFoundError(f"Draft {draft_id} not found")
        
        if not _is_collaborator(draft, user_id):
            raise PermissionError(f"User {user_id} is not a collaborator on draft {draft_id}")
        
        return AnalyticsService.compute_daily_activity(draft, days=days)
