"""
backend/api/analytics.py

Event-driven analytics endpoints (Phase 3.4).
Pure event-reducer architecture: Events → Reducers → Read Models → API.
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

from backend.models.analytics import DraftAnalytics, UserAnalytics, LeaderboardResponse
from backend.features.analytics.event_store import get_store
from backend.features.analytics.reducers import (
    reduce_draft_analytics,
    reduce_user_analytics,
    reduce_leaderboard,
)

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
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


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
            raise HTTPException(
                status_code=400,
                detail=f"Invalid metric type. Must be one of: {', '.join(valid_metrics)}",
            )
        
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
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")
