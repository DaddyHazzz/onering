"""
backend/features/analytics/reducers.py

Pure deterministic reducers for analytics (Phase 3.4).
All reducers: (events, now) -> immutable read model.
"""

from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Set
from backend.models.analytics import (
    DraftAnalytics,
    UserAnalytics,
    LeaderboardEntry,
    LeaderboardResponse,
)
from backend.features.analytics.event_store import Event


def reduce_draft_analytics(
    draft_id: str,
    events: List[Event],
    now: Optional[datetime] = None
) -> DraftAnalytics:
    """
    Reduce events to draft analytics.
    
    Pure function: same events + same now => identical output.
    
    Args:
        draft_id: Draft to analyze
        events: All events (will be filtered to this draft)
        now: Fixed timestamp for deterministic results
    
    Returns:
        DraftAnalytics (immutable)
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    # Filter events for this draft
    draft_events = [e for e in events if e.data.get("draft_id") == draft_id]
    
    # Count views (unique DraftViewed events)
    view_events = [e for e in draft_events if e.event_type == "DraftViewed"]
    views = len(view_events)
    
    # Count shares (DraftShared events)
    share_events = [e for e in draft_events if e.event_type == "DraftShared"]
    shares = len(share_events)
    
    # Count segments (SegmentAdded events)
    segment_events = [e for e in draft_events if e.event_type == "SegmentAdded"]
    segments_count = max(1, len(segment_events))  # At least 1 (creator's initial segment)
    
    # Count unique contributors (creator + segment authors)
    contributors: Set[str] = set()
    for e in draft_events:
        if e.event_type == "DraftCreated":
            contributors.add(e.data.get("creator_id", ""))
        elif e.event_type == "SegmentAdded":
            contributors.add(e.data.get("contributor_id", ""))
    contributors_count = max(1, len(contributors))  # At least 1 (creator)
    
    # Count ring passes (RINGPassed events)
    ring_pass_events = [e for e in draft_events if e.event_type == "RINGPassed"]
    ring_passes_count = len(ring_pass_events)
    
    # Last activity: most recent event timestamp
    last_activity_at: Optional[datetime] = None
    if draft_events:
        activity_events = [
            e for e in draft_events
            if e.event_type in ("SegmentAdded", "RINGPassed", "DraftPublished")
        ]
        if activity_events:
            last_activity_at = max(e.timestamp for e in activity_events)
    
    return DraftAnalytics(
        draft_id=draft_id,
        views=views,
        shares=shares,
        segments_count=segments_count,
        contributors_count=contributors_count,
        ring_passes_count=ring_passes_count,
        last_activity_at=last_activity_at,
        computed_at=now
    )


def reduce_user_analytics(
    user_id: str,
    events: List[Event],
    now: Optional[datetime] = None
) -> UserAnalytics:
    """
    Reduce events to user analytics.
    
    Pure function: same events + same now => identical output.
    
    Args:
        user_id: User to analyze
        events: All events (will be filtered to this user)
        now: Fixed timestamp for deterministic results
    
    Returns:
        UserAnalytics (immutable)
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    # Drafts created (DraftCreated events by this user)
    created_events = [
        e for e in events
        if e.event_type == "DraftCreated" and e.data.get("creator_id") == user_id
    ]
    drafts_created = len(created_events)
    created_draft_ids = {e.data.get("draft_id") for e in created_events}
    
    # Drafts contributed to (SegmentAdded events in drafts user didn't create)
    contributed_events = [
        e for e in events
        if e.event_type == "SegmentAdded" and
           e.data.get("contributor_id") == user_id and
           e.data.get("draft_id") not in created_draft_ids
    ]
    contributed_draft_ids = {e.data.get("draft_id") for e in contributed_events}
    drafts_contributed = len(contributed_draft_ids)
    
    # Segments written (all SegmentAdded events by this user)
    segment_events = [
        e for e in events
        if e.event_type == "SegmentAdded" and e.data.get("contributor_id") == user_id
    ]
    segments_written = len(segment_events)
    
    # Rings held (RINGPassed events where to_user_id is this user)
    ring_received_events = [
        e for e in events
        if e.event_type == "RINGPassed" and e.data.get("to_user_id") == user_id
    ]
    rings_held_count = len(ring_received_events)
    
    # Average time holding ring (stub: assume 30 minutes per ring pass)
    # Phase 3.5: calculate actual hold duration from event sequences
    avg_time_holding_ring_minutes = 30.0 if rings_held_count > 0 else 0.0
    
    # Last activity: most recent event timestamp
    user_events = [
        e for e in events
        if (e.event_type == "DraftCreated" and e.data.get("creator_id") == user_id) or
           (e.event_type == "SegmentAdded" and e.data.get("contributor_id") == user_id) or
           (e.event_type == "RINGPassed" and e.data.get("to_user_id") == user_id)
    ]
    last_active_at: Optional[datetime] = None
    if user_events:
        last_active_at = max(e.timestamp for e in user_events)
    
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


def reduce_leaderboard(
    metric_type: str,
    events: List[Event],
    now: Optional[datetime] = None
) -> LeaderboardResponse:
    """
    Reduce events to leaderboard.
    
    Pure function: same events + same now => identical output.
    Stable sort: by score (desc), then user_id (asc) for tie-breaking.
    
    Args:
        metric_type: "collaboration" | "momentum" | "consistency"
        events: All events
        now: Fixed timestamp for deterministic results
    
    Returns:
        LeaderboardResponse (immutable, max 10 entries)
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    # Get all unique user IDs from events
    user_ids: Set[str] = set()
    for e in events:
        if e.event_type == "DraftCreated":
            user_ids.add(e.data.get("creator_id", ""))
        elif e.event_type == "SegmentAdded":
            user_ids.add(e.data.get("contributor_id", ""))
        elif e.event_type == "RINGPassed":
            user_ids.add(e.data.get("to_user_id", ""))
    
    # Compute analytics for each user
    user_analytics_map = {
        uid: reduce_user_analytics(uid, events, now)
        for uid in user_ids if uid
    }
    
    # Compute scores based on metric type
    user_scores: List[tuple[float, str, UserAnalytics]] = []
    for uid, analytics in user_analytics_map.items():
        if metric_type == "collaboration":
            # Collaboration = segments×3 + rings×2 + drafts_contributed
            score = (
                analytics.segments_written * 3 +
                analytics.rings_held_count * 2 +
                analytics.drafts_contributed
            )
        elif metric_type == "momentum":
            # Momentum: stub (Phase 3.5 will integrate with momentum service)
            # For now, use segments + drafts created as proxy
            score = analytics.segments_written + analytics.drafts_created * 5
        elif metric_type == "consistency":
            # Consistency = drafts_created×5 + drafts_contributed×2
            score = (
                analytics.drafts_created * 5 +
                analytics.drafts_contributed * 2
            )
        else:
            score = 0.0
        
        user_scores.append((score, uid, analytics))
    
    # Stable sort: score descending, user_id ascending (tie-breaker)
    user_scores.sort(key=lambda x: (-x[0], x[1]))
    
    # Take top 10
    top_10 = user_scores[:10]
    
    # Create leaderboard entries
    entries: List[LeaderboardEntry] = []
    for position, (score, uid, analytics) in enumerate(top_10, start=1):
        # Display name: stub (Phase 3.5 will fetch from Clerk)
        display_name = f"user_{uid[:6]}"
        
        # Metric label (human-readable)
        if metric_type == "collaboration":
            metric_label = f"{analytics.segments_written} segments • {analytics.rings_held_count} rings"
        elif metric_type == "momentum":
            metric_label = f"{analytics.segments_written} segments"
        elif metric_type == "consistency":
            metric_label = f"{analytics.drafts_created} created • {analytics.drafts_contributed} contributed"
        else:
            metric_label = f"{score:.0f} points"
        
        # Supportive insight (never comparative)
        insight = _get_insight(metric_type, position, score)
        
        entries.append(LeaderboardEntry(
            position=position,
            user_id=uid,
            display_name=display_name,
            avatar_url=None,  # Phase 3.5: fetch from Clerk
            metric_value=score,
            metric_label=metric_label,
            insight=insight
        ))
    
    # Supportive message (never comparative)
    message = _get_leaderboard_message(metric_type)
    
    return LeaderboardResponse(
        metric_type=metric_type,  # type: ignore
        entries=entries,
        computed_at=now,
        message=message
    )


def _get_insight(metric_type: str, position: int, score: float) -> str:
    """
    Generate supportive insight based on position and score.
    Never comparative, never shaming.
    
    Args:
        metric_type: Type of leaderboard
        position: Position (1-10)
        score: Metric value
    
    Returns:
        Supportive insight string
    """
    if score == 0:
        return "Every journey starts with a first step!"
    
    if position == 1:
        return "Leading by example—great contributions!"
    elif position <= 3:
        return "Strong momentum—keep building!"
    elif position <= 5:
        return "You're growing your impact!"
    else:
        return "Building consistency—keep going!"


def _get_leaderboard_message(metric_type: str) -> str:
    """
    Get supportive header message for leaderboard.
    Never comparative.
    
    Args:
        metric_type: Type of leaderboard
    
    Returns:
        Supportive message string
    """
    if metric_type == "collaboration":
        return "Community highlights: creators shaping work together"
    elif metric_type == "momentum":
        return "Momentum builders: consistency over time"
    elif metric_type == "consistency":
        return "Consistent creators: showing up and iterating"
    else:
        return "Community highlights"
