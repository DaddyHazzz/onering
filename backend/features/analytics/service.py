"""
backend/features/analytics/service.py
Analytics computation: deterministic, safety-first, insight-oriented.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from backend.models.analytics import DraftAnalytics, UserAnalytics, LeaderboardEntry, LeaderboardResponse
from backend.models.collab import CollabDraft
from backend.models.momentum import MomentumSnapshot
import math


# STUB: Phase 3.5→PostgreSQL
# In-memory stores for analytics
_draft_analytics_store: Dict[str, DraftAnalytics] = {}
_user_analytics_store: Dict[str, UserAnalytics] = {}
_draft_views_store: Dict[str, int] = {}  # draft_id -> view count
_draft_shares_store: Dict[str, int] = {}  # draft_id -> share count


def clear_store() -> None:
    """Clear all in-memory stores (for testing)."""
    global _draft_analytics_store, _user_analytics_store, _draft_views_store, _draft_shares_store
    _draft_analytics_store.clear()
    _user_analytics_store.clear()
    _draft_views_store.clear()
    _draft_shares_store.clear()


def record_draft_view(draft_id: str) -> None:
    """Record that a draft was viewed."""
    _draft_views_store[draft_id] = _draft_views_store.get(draft_id, 0) + 1


def record_draft_share(draft_id: str) -> None:
    """Record that a draft was shared."""
    _draft_shares_store[draft_id] = _draft_shares_store.get(draft_id, 0) + 1


def compute_draft_analytics(draft: CollabDraft, now: Optional[datetime] = None) -> DraftAnalytics:
    """
    Compute analytics for a draft.
    
    Deterministic: same draft + same now => same output
    
    Args:
        draft: CollabDraft instance
        now: Fixed timestamp for reproducible results (optional)
    
    Returns:
        DraftAnalytics with all metrics
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    # Clamp now to UTC if not already
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    # Views and shares from tracking stores
    views = _draft_views_store.get(draft.draft_id, 0)
    shares = _draft_shares_store.get(draft.draft_id, 0)
    
    # Segments count
    segments_count = len(draft.segments)
    
    # Contributors count (creator + collaborators + unique segment authors)
    contributor_ids = {draft.creator_id}
    for segment in draft.segments:
        contributor_ids.add(segment.user_id)
    for collab_id in draft.collaborators:
        contributor_ids.add(collab_id)
    contributors_count = len(contributor_ids)
    
    # Ring passes (history length - 1, since initial holder is not a "pass")
    ring_passes_count = len(draft.ring_state.holders_history) if draft.ring_state.holders_history else 0
    
    # Last activity: most recent segment or ring pass
    last_activity_at: Optional[datetime] = None
    if draft.segments:
        last_segment_time = max(seg.created_at for seg in draft.segments)
        last_activity_at = last_segment_time
    if draft.ring_state.last_passed_at and (last_activity_at is None or draft.ring_state.last_passed_at > last_activity_at):
        last_activity_at = draft.ring_state.last_passed_at
    
    return DraftAnalytics(
        draft_id=draft.draft_id,
        views=views,
        shares=shares,
        segments_count=segments_count,
        contributors_count=contributors_count,
        ring_passes_count=ring_passes_count,
        last_activity_at=last_activity_at,
        computed_at=now
    )


def compute_user_analytics(
    user_id: str,
    drafts: List[CollabDraft],
    now: Optional[datetime] = None
) -> UserAnalytics:
    """
    Compute analytics for a user across all their drafts.
    
    Deterministic: same user + same drafts + same now => same output
    
    Args:
        user_id: Clerk user ID
        drafts: All drafts this user is involved with
        now: Fixed timestamp for reproducible results (optional)
    
    Returns:
        UserAnalytics with all metrics
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    drafts_created = 0
    drafts_contributed = 0
    segments_written = 0
    rings_held_count = 0
    ring_hold_durations: List[float] = []
    last_active_at: Optional[datetime] = None
    
    for draft in drafts:
        # Count created drafts
        if draft.creator_id == user_id:
            drafts_created += 1
        
        # Count contributed segments
        user_segments = [seg for seg in draft.segments if seg.user_id == user_id]
        if user_segments:
            if draft.creator_id != user_id:
                drafts_contributed += 1
            segments_written += len(user_segments)
        
        # Count rings held and measure hold duration
        if draft.ring_state.holders_history:
            for i, holder_id in enumerate(draft.ring_state.holders_history):
                if holder_id == user_id:
                    rings_held_count += 1
                    
                    # Try to measure duration until next pass
                    if i + 1 < len(draft.ring_state.holders_history):
                        # Next holder exists, measure time between passes (using indices as proxy)
                        # In real system, we'd have timestamps for each pass
                        # For now, estimate as 30 minutes per pass (stub)
                        ring_hold_durations.append(30.0)
        
        # Update last activity
        for segment in user_segments:
            if last_active_at is None or segment.created_at > last_active_at:
                last_active_at = segment.created_at
    
    # Compute average ring hold duration
    avg_time_holding_ring_minutes = 0.0
    if ring_hold_durations:
        avg_time_holding_ring_minutes = sum(ring_hold_durations) / len(ring_hold_durations)
    
    return UserAnalytics(
        user_id=user_id,
        drafts_created=drafts_created,
        drafts_contributed=drafts_contributed,
        segments_written=segments_written,
        rings_held_count=rings_held_count,
        avg_time_holding_ring_minutes=avg_time_holding_ring_minutes,
        last_active_at=last_active_at,
        computed_at=now
    )


def get_leaderboard(
    metric_type: str,
    all_drafts: List[CollabDraft],
    user_analytics_map: Dict[str, UserAnalytics],
    momentum_scores: Dict[str, float],
    now: Optional[datetime] = None
) -> LeaderboardResponse:
    """
    Generate a leaderboard for given metric type.
    
    Deterministic: same inputs + same now => same entries in same order
    
    Args:
        metric_type: "collaboration" | "momentum" | "consistency"
        all_drafts: All drafts in system
        user_analytics_map: Pre-computed user analytics
        momentum_scores: Pre-computed momentum scores by user_id
        now: Fixed timestamp for reproducible results
    
    Returns:
        LeaderboardResponse with top 10 entries
    """
    if now is None:
        now = datetime.now(timezone.utc)
    
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    entries: List[LeaderboardEntry] = []
    
    if metric_type == "collaboration":
        # Leaderboard by collaboration activity: segments + rings + drafts contributed
        user_scores: List[tuple] = []
        for user_id, analytics in user_analytics_map.items():
            # Score = segments_written * 3 + rings_held * 2 + drafts_contributed
            score = (analytics.segments_written * 3) + (analytics.rings_held_count * 2) + (analytics.drafts_contributed)
            user_scores.append((score, user_id, analytics))
        
        # Sort by score descending, then by user_id (tie-breaker for determinism)
        user_scores.sort(key=lambda x: (-x[0], x[1]))
        
        for i, (score, user_id, analytics) in enumerate(user_scores[:10]):
            position = i + 1
            metric_label = f"{analytics.segments_written} segments • {analytics.rings_held_count} rings"
            insight = _get_collaboration_insight(position, analytics)
            
            entry = LeaderboardEntry(
                position=position,
                user_id=user_id,
                display_name=f"user_{user_id[:8]}",  # Stub: Phase 3.5 will have real names
                avatar_url=None,  # Stub: Phase 3.5 will have avatars
                metric_value=float(score),
                metric_label=metric_label,
                insight=insight
            )
            entries.append(entry)
    
    elif metric_type == "momentum":
        # Leaderboard by momentum score
        user_scores: List[tuple] = []
        for user_id, score in momentum_scores.items():
            user_scores.append((score, user_id))
        
        # Sort by score descending, then by user_id (tie-breaker)
        user_scores.sort(key=lambda x: (-x[0], x[1]))
        
        for i, (score, user_id) in enumerate(user_scores[:10]):
            position = i + 1
            metric_label = f"{score:.1f} momentum"
            insight = _get_momentum_insight(position, score)
            
            entry = LeaderboardEntry(
                position=position,
                user_id=user_id,
                display_name=f"user_{user_id[:8]}",
                avatar_url=None,
                metric_value=score,
                metric_label=metric_label,
                insight=insight
            )
            entries.append(entry)
    
    elif metric_type == "consistency":
        # Leaderboard by consistency: drafts created + contributions
        user_scores: List[tuple] = []
        for user_id, analytics in user_analytics_map.items():
            # Score = drafts_created * 5 + drafts_contributed * 2
            score = (analytics.drafts_created * 5) + (analytics.drafts_contributed * 2)
            user_scores.append((score, user_id, analytics))
        
        # Sort by score descending, then by user_id
        user_scores.sort(key=lambda x: (-x[0], x[1]))
        
        for i, (score, user_id, analytics) in enumerate(user_scores[:10]):
            position = i + 1
            metric_label = f"{analytics.drafts_created} created • {analytics.drafts_contributed} contributed"
            insight = _get_consistency_insight(position, analytics)
            
            entry = LeaderboardEntry(
                position=position,
                user_id=user_id,
                display_name=f"user_{user_id[:8]}",
                avatar_url=None,
                metric_value=float(score),
                metric_label=metric_label,
                insight=insight
            )
            entries.append(entry)
    
    message = _get_leaderboard_message(metric_type)
    
    return LeaderboardResponse(
        metric_type=metric_type,
        entries=entries,
        computed_at=now,
        message=message
    )


def _get_collaboration_insight(position: int, analytics: UserAnalytics) -> str:
    """Supportive insight for collaboration leaderboard."""
    if position == 1:
        return "Leading by example—great contributions!"
    elif position <= 3:
        return "Strong collaboration—keep it up!"
    elif position <= 5:
        return "Good momentum on shared work!"
    else:
        return "Growing collaboration skills!"


def _get_momentum_insight(position: int, score: float) -> str:
    """Supportive insight for momentum leaderboard."""
    if score >= 80:
        return "Exceptional momentum—sustaining excellence!"
    elif score >= 60:
        return "Strong momentum—great consistency!"
    elif score >= 40:
        return "Growing momentum—keep building!"
    else:
        return "Starting to build momentum!"


def _get_consistency_insight(position: int, analytics: UserAnalytics) -> str:
    """Supportive insight for consistency leaderboard."""
    total = analytics.drafts_created + analytics.drafts_contributed
    if total >= 10:
        return "Consistent creator—impressive dedication!"
    elif total >= 5:
        return "Regular contributor—great habit!"
    else:
        return "Building your creation rhythm!"


def _get_leaderboard_message(metric_type: str) -> str:
    """Supportive header message (never comparative)."""
    if metric_type == "collaboration":
        return "Community highlights: creators shaping work together"
    elif metric_type == "momentum":
        return "Momentum matters: sustaining effort over time"
    elif metric_type == "consistency":
        return "Commitment: showing up, creating, and iterating"
    return "Creator community insights"
