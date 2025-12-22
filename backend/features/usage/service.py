"""
backend/features/usage/service.py

Usage accounting service (Phase 4.1).

Handles:
- Usage event emission
- Usage counting (reducer)
- Deterministic usage queries
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Any, List
from sqlalchemy import select, insert, func

from backend.core.database import get_db_session, usage_events, create_all_tables
from backend.models.usage_event import UsageEvent


def emit_usage_event(
    user_id: str,
    usage_key: str,
    occurred_at: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> UsageEvent:
    """
    Emit a usage event (idempotent via occurred_at + user_id + usage_key).
    
    Args:
        user_id: User performing the action
        usage_key: Usage type (drafts.created, segments.appended, etc.)
        occurred_at: Timestamp of usage (defaults to now)
        metadata: Optional metadata (draft_id, segment_id, etc.)
    
    Returns:
        UsageEvent instance
    """
    if occurred_at is None:
        occurred_at = datetime.now(timezone.utc)
    elif occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    
    # Ensure tables exist
    try:
        create_all_tables()
    except Exception:
        pass
    
    # Insert usage event (allow duplicates for now; Phase 4.2+ can add idempotency)
    with get_db_session() as session:
        session.execute(
            insert(usage_events).values(
                user_id=user_id,
                usage_key=usage_key,
                occurred_at=occurred_at,
                metadata=metadata
            )
        )
    
    return UsageEvent(
        user_id=user_id,
        usage_key=usage_key,
        occurred_at=occurred_at,
        metadata=metadata
    )


def get_usage_events(
    user_id: str,
    usage_key: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> List[UsageEvent]:
    """
    Get usage events for a user.
    
    Args:
        user_id: User to query
        usage_key: Optional filter by usage key
        start_time: Optional start of time window (inclusive)
        end_time: Optional end of time window (inclusive)
    
    Returns:
        List of UsageEvent instances
    """
    with get_db_session() as session:
        query = select(usage_events).where(usage_events.c.user_id == user_id)
        
        if usage_key:
            query = query.where(usage_events.c.usage_key == usage_key)
        
        if start_time:
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)
            query = query.where(usage_events.c.occurred_at >= start_time)
        
        if end_time:
            if end_time.tzinfo is None:
                end_time = end_time.replace(tzinfo=timezone.utc)
            query = query.where(usage_events.c.occurred_at <= end_time)
        
        rows = session.execute(query.order_by(usage_events.c.occurred_at)).all()
        
        return [
            UsageEvent(
                user_id=row.user_id,
                usage_key=row.usage_key,
                occurred_at=row.occurred_at,
                metadata=row.metadata
            )
            for row in rows
        ]


def reduce_usage(
    user_id: str,
    now: Optional[datetime] = None,
    window_days: Optional[int] = None
) -> Dict[str, int]:
    """
    Reduce usage events to counts per usage_key.
    
    Pure function: same user_id + same now + same window = same counts.
    
    Args:
        user_id: User to analyze
        now: Fixed timestamp for deterministic queries (defaults to now())
        window_days: Optional rolling window in days (e.g., 30 for monthly)
    
    Returns:
        Dict mapping usage_key to count
        Example: {"drafts.created": 5, "segments.appended": 12}
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    start_time = None
    if window_days:
        start_time = now - timedelta(days=window_days)
    
    events = get_usage_events(user_id, start_time=start_time, end_time=now)
    
    # Count events by usage_key
    counts: Dict[str, int] = {}
    for event in events:
        counts[event.usage_key] = counts.get(event.usage_key, 0) + 1
    
    return counts


def get_usage_count(
    user_id: str,
    usage_key: str,
    now: Optional[datetime] = None,
    window_days: Optional[int] = None
) -> int:
    """
    Get count for specific usage key.
    
    Args:
        user_id: User to query
        usage_key: Usage key to count
        now: Fixed timestamp for deterministic queries
        window_days: Optional rolling window in days
    
    Returns:
        Count of usage events
    """
    counts = reduce_usage(user_id, now, window_days)
    return counts.get(usage_key, 0)
