"""
Public Creator Profile API

GET /v1/profile/public?handle=... or GET /v1/profile/public?user_id=...

Returns public-facing creator profile with:
- Streak info (current, longest)
- Today's momentum + 7-day history
- Recent published posts (max 5)
- Profile summary
- Archetype (primary + secondary + explanation)

Safe for public sharing; only returns appropriate data.
"""

from fastapi import APIRouter, HTTPException, Query, HTTPException
from datetime import datetime, timezone
from typing import Optional, List
from pydantic import BaseModel
from backend.features.archetypes import service as archetype_service

router = APIRouter(prefix="/v1/profile", tags=["profile"])


# ============ Response Models ============


class StreakSummary(BaseModel):
    """Streak information for profile display."""
    current_length: int
    longest_length: int
    status: str  # "active", "on_break", "building"
    last_active_date: str  # ISO date


class RecentPost(BaseModel):
    """Brief post preview for profile."""
    id: str
    platform: str  # "x", "instagram", "linkedin"
    content: str  # First 140 chars
    created_at: str  # ISO datetime


class PublicProfileResponse(BaseModel):
    """Public creator profile."""
    user_id: str
    handle: Optional[str] = None
    display_name: str
    streak: StreakSummary
    momentum_today: dict  # Full MomentumSnapshot
    momentum_weekly: List[dict]  # Array of MomentumSnapshot (7 days)
    recent_posts: List[RecentPost]
    profile_summary: str  # Short deterministic description
    archetype: Optional[dict] = None  # { primary, secondary, explanation, updatedAt }
    computed_at: str  # UTC timestamp


# ============ Deterministic Stubs ============


def _stub_streak_for_user(user_id: str) -> StreakSummary:
    """
    Deterministic stub streak data.
    
    In production, read from StreakService.
    For now, generate deterministic based on user_id hash.
    """
    # Simple deterministic hash-based generation
    hash_val = hash(user_id) % 31
    current_length = max(1, hash_val)
    longest_length = max(current_length, (hash_val + 5) % 30)
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    status = "active" if current_length >= 3 else "building"
    
    return StreakSummary(
        current_length=current_length,
        longest_length=longest_length,
        status=status,
        last_active_date=today,
    )


def _stub_momentum_today_for_user(user_id: str) -> dict:
    """
    Deterministic stub momentum snapshot for today.
    
    In production, call MomentumService.compute_today_momentum(user_id).
    """
    from datetime import datetime, timezone
    
    today = datetime.now(timezone.utc).date().isoformat()
    
    # Deterministic but varied score based on user_id
    hash_val = hash(user_id) % 100
    score = 40.0 + (hash_val * 0.6)  # Ranges 40-100
    
    trend = "up" if hash_val % 3 == 0 else ("down" if hash_val % 3 == 1 else "flat")
    
    return {
        "userId": user_id,
        "date": today,
        "score": round(score, 1),
        "trend": trend,
        "components": {
            "streakComponent": round((hash_val % 25) * 0.8, 1),
            "consistencyComponent": round((hash_val % 10) * 0.7, 1),
            "challengeComponent": 15.0 if hash_val % 2 == 0 else 0.0,
            "coachComponent": round((hash_val % 10) * 0.5, 1),
        },
        "nextActionHint": "Keep building momentum today.",
        "computedAt": datetime.now(timezone.utc).isoformat(),
    }


def _stub_momentum_weekly_for_user(user_id: str) -> List[dict]:
    """
    Deterministic stub weekly momentum (7 days, most recent first).
    
    In production, call MomentumService.compute_weekly_momentum(user_id).
    """
    from datetime import datetime, timedelta, timezone
    
    today = datetime.now(timezone.utc).date()
    snapshots = []
    
    for days_back in range(7):
        date = today - timedelta(days=days_back)
        date_str = date.isoformat()
        
        # Deterministic variation based on user_id + day
        hash_val = (hash(user_id) + days_back * 13) % 100
        score = 40.0 + (hash_val * 0.6)
        trend = "up" if hash_val % 3 == 0 else ("down" if hash_val % 3 == 1 else "flat")
        
        snapshots.append({
            "userId": user_id,
            "date": date_str,
            "score": round(score, 1),
            "trend": trend,
            "components": {
                "streakComponent": round((hash_val % 25) * 0.8, 1),
                "consistencyComponent": round((hash_val % 10) * 0.7, 1),
                "challengeComponent": 15.0 if hash_val % 2 == 0 else 0.0,
                "coachComponent": round((hash_val % 10) * 0.5, 1),
            },
            "nextActionHint": "Keep building momentum.",
            "computedAt": datetime.now(timezone.utc).isoformat(),
        })
    
    return snapshots


def _stub_recent_posts_for_user(user_id: str) -> List[RecentPost]:
    """
    Deterministic stub recent posts.
    
    In production, query post history from analytics/posts service.
    For now, return empty or 1-2 stub posts based on user_id.
    """
    hash_val = hash(user_id) % 10
    
    if hash_val < 5:
        # Return empty
        return []
    else:
        # Return 1 stub post
        today = datetime.now(timezone.utc)
        return [
            RecentPost(
                id=f"post_{user_id[:8]}_1",
                platform="x",
                content="Just shipped something I'm proud of. Momentum building...",
                created_at=today.isoformat(),
            )
        ]


def _profile_summary_for_user(user_id: str, streak: StreakSummary, momentum_score: float) -> str:
    """
    Deterministic profile summary line.
    
    Never uses LLM. Always supportive, never punitive.
    """
    if momentum_score >= 80.0:
        base = "🚀 Creator in flow"
    elif momentum_score >= 60.0:
        base = "✨ Building momentum"
    elif momentum_score >= 40.0:
        base = "📈 Growing consistency"
    else:
        base = "💪 Finding rhythm"
    
    if streak.current_length >= 20:
        return f"{base} • {streak.current_length}-day streak"
    elif streak.current_length >= 7:
        return f"{base} • Strong streak"
    else:
        return f"{base} • Learning"


# ============ Internal Functions ============


async def get_public_profile(
    handle: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    """
    Internal function to get public creator profile.
    Can be called directly or from route handler.
    
    Args:
        handle: Creator handle (e.g., @alice) — preferred
        user_id: User ID (e.g., user_123) — fallback
    
    Returns: dict with 'data' key containing PublicProfileResponse
    """
    try:
        if not handle and not user_id:
            raise ValueError("Either 'handle' or 'user_id' is required")
        
        # Resolve handle to user_id if needed
        if handle:
            # In production, look up handle in user DB
            # For now, treat handle as user_id for simplicity
            user_id = str(handle).lstrip("@")
        
        if not user_id:
            raise ValueError("Could not resolve profile")
        
        user_id = str(user_id)
        
        # Gather profile data
        streak = _stub_streak_for_user(user_id)
        momentum_today = _stub_momentum_today_for_user(user_id)
        momentum_weekly = _stub_momentum_weekly_for_user(user_id)
        recent_posts = _stub_recent_posts_for_user(user_id)
        profile_summary = _profile_summary_for_user(user_id, streak, momentum_today["score"])
        
        # Get archetype (public subset)
        archetype_snapshot = archetype_service.get_snapshot(user_id)
        archetype_data = archetype_snapshot.to_public_dict()
        
        # Build response
        profile = PublicProfileResponse(
            user_id=user_id,
            handle=handle or None,
            display_name=f"Creator {user_id[:8]}",
            streak=streak,
            momentum_today=momentum_today,
            momentum_weekly=momentum_weekly,
            recent_posts=recent_posts,
            profile_summary=profile_summary,
            archetype=archetype_data,
            computed_at=datetime.now(timezone.utc).isoformat(),
        )
        
        return {"data": profile.model_dump()}
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving profile: {str(e)}")


# ============ Endpoints ============


@router.get("/public")
async def get_public_profile_route(
    handle: Optional[str] = Query(None, description="Creator handle (preferred)"),
    user_id: Optional[str] = Query(None, description="User ID (fallback)"),
) -> dict:
    """
    Get public creator profile.
    
    Query params:
        handle: Creator handle (e.g., @alice) — preferred, uses name
        user_id: User ID (e.g., user_123) — fallback
    
    Returns: PublicProfileResponse as dict
    
    Example:
        GET /v1/profile/public?handle=alice
        GET /v1/profile/public?user_id=user_123
    """
    return await get_public_profile(handle=handle, user_id=user_id)
