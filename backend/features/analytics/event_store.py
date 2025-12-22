"""
backend/features/analytics/event_store.py

Append-only event store for analytics (Phase 3.4).
In-memory implementation (Phase 3.5 will migrate to PostgreSQL).
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# Event types aligned with collaboration domain
class Event(BaseModel):
    """Base event model."""
    model_config = ConfigDict(frozen=True)
    
    event_type: str
    timestamp: datetime
    data: Dict[str, Any]


class DraftCreatedEvent(BaseModel):
    """Draft was created by a user."""
    model_config = ConfigDict(frozen=True)
    
    event_type: str = "DraftCreated"
    draft_id: str
    creator_id: str
    created_at: datetime


class DraftViewedEvent(BaseModel):
    """Draft was viewed by a user."""
    model_config = ConfigDict(frozen=True)
    
    event_type: str = "DraftViewed"
    draft_id: str
    user_id: str
    viewed_at: datetime


class DraftSharedEvent(BaseModel):
    """Draft share card was generated/shared."""
    model_config = ConfigDict(frozen=True)
    
    event_type: str = "DraftShared"
    draft_id: str
    user_id: str
    shared_at: datetime


class SegmentAddedEvent(BaseModel):
    """Segment was added to a draft."""
    model_config = ConfigDict(frozen=True)
    
    event_type: str = "SegmentAdded"
    draft_id: str
    segment_id: str
    contributor_id: str
    added_at: datetime


class RINGPassedEvent(BaseModel):
    """RING was passed from one user to another."""
    model_config = ConfigDict(frozen=True)
    
    event_type: str = "RINGPassed"
    draft_id: str
    from_user_id: str
    to_user_id: str
    passed_at: datetime


class DraftPublishedEvent(BaseModel):
    """Draft was published."""
    model_config = ConfigDict(frozen=True)
    
    event_type: str = "DraftPublished"
    draft_id: str
    publisher_id: str
    published_at: datetime


# STUB: Phase 3.5→PostgreSQL
# In-memory event store (append-only log)
_events: List[Event] = []
_idempotency_keys: Dict[str, bool] = {}


class EventStore:
    """
    Append-only event store for analytics.
    
    Phase 3.4: In-memory implementation.
    Phase 3.5: PostgreSQL persistence.
    """
    
    @staticmethod
    def append(event: Event, idempotency_key: str) -> bool:
        """
        Append event to store with idempotency guarantee.
        
        Args:
            event: Event to append
            idempotency_key: Unique key to prevent duplicate processing
        
        Returns:
            True if event was appended, False if key already seen
        """
        if idempotency_key in _idempotency_keys:
            return False  # Already processed
        
        _events.append(event)
        _idempotency_keys[idempotency_key] = True
        return True
    
    @staticmethod
    def get_events(
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None
    ) -> List[Event]:
        """
        Retrieve events in time window.
        
        Args:
            start_time: Start of time window (inclusive, optional)
            end_time: End of time window (inclusive, optional)
            event_type: Filter by event type (optional)
        
        Returns:
            List of events matching filters (always a copy, not a reference)
        """
        filtered = list(_events)  # Always start with a copy
        
        # Apply time filters
        if start_time or end_time:
            filtered = [
                e for e in filtered
                if (start_time is None or e.timestamp >= start_time) and
                   (end_time is None or e.timestamp <= end_time)
            ]
        
        # Apply event type filter
        if event_type:
            filtered = [e for e in filtered if e.event_type == event_type]
        
        return filtered
    
    @staticmethod
    def clear() -> None:
        """
        Clear all events and idempotency keys.
        FOR TESTING ONLY.
        """
        global _events, _idempotency_keys
        _events.clear()
        _idempotency_keys.clear()
    
    @staticmethod
    def count() -> int:
        """Return total number of events in store."""
        return len(_events)


# Convenience function for creating events with proper timestamps
def create_event(
    event_type: str,
    data: Dict[str, Any],
    now: Optional[datetime] = None
) -> Event:
    """
    Create event with proper timestamp handling.
    
    Args:
        event_type: Type of event (DraftCreated, DraftViewed, etc.)
        data: Event data
        now: Fixed timestamp for deterministic testing (optional)
    
    Returns:
        Event instance
    """
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    
    return Event(
        event_type=event_type,
        timestamp=now,
        data=data
    )


def generate_idempotency_key(event_type: str, **kwargs) -> str:
    """
    Generate idempotency key from event attributes.
    
    Examples:
        - DraftCreated: f"DraftCreated:{draft_id}"
        - DraftViewed: f"DraftViewed:{draft_id}:{user_id}:{bucket}"
        - SegmentAdded: f"SegmentAdded:{segment_id}"
    
    Args:
        event_type: Type of event
        **kwargs: Event-specific attributes
    
    Returns:
        Idempotency key (unique string)
    """
    parts = [event_type]
    for key in sorted(kwargs.keys()):
        parts.append(f"{key}={kwargs[key]}")
    return ":".join(parts)
