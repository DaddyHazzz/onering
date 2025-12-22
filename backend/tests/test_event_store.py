"""
backend/tests/test_event_store.py

Tests for event store (Phase 3.4).
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.features.analytics.event_store import (
    EventStore,
    Event,
    DraftCreatedEvent,
    DraftViewedEvent,
    SegmentAddedEvent,
    RINGPassedEvent,
    create_event,
    generate_idempotency_key,
)


@pytest.fixture(autouse=True)
def clear_event_store():
    """Clear event store before each test."""
    EventStore.clear()
    yield
    EventStore.clear()


class TestEventStoreBasics:
    """Test basic event store operations."""
    
    def test_append_event_success(self):
        """Appending a new event with unique key succeeds."""
        event = create_event("DraftCreated", {"draft_id": "draft-123"})
        result = EventStore.append(event, idempotency_key="test-key-1")
        
        assert result is True
        assert EventStore.count() == 1
    
    def test_append_duplicate_key_fails(self):
        """Appending event with same idempotency key fails."""
        event1 = create_event("DraftCreated", {"draft_id": "draft-123"})
        event2 = create_event("DraftCreated", {"draft_id": "draft-456"})
        
        result1 = EventStore.append(event1, idempotency_key="test-key-1")
        result2 = EventStore.append(event2, idempotency_key="test-key-1")
        
        assert result1 is True
        assert result2 is False  # Duplicate key
        assert EventStore.count() == 1  # Only one event stored
    
    def test_get_events_all(self):
        """get_events with no filters returns all events."""
        event1 = create_event("DraftCreated", {"draft_id": "draft-123"})
        event2 = create_event("DraftViewed", {"draft_id": "draft-123"})
        
        EventStore.append(event1, idempotency_key="key-1")
        EventStore.append(event2, idempotency_key="key-2")
        
        events = EventStore.get_events()
        assert len(events) == 2
    
    def test_clear_store(self):
        """clear() removes all events and idempotency keys."""
        event = create_event("DraftCreated", {"draft_id": "draft-123"})
        EventStore.append(event, idempotency_key="key-1")
        
        EventStore.clear()
        
        assert EventStore.count() == 0
        # Can re-add with same key after clear
        result = EventStore.append(event, idempotency_key="key-1")
        assert result is True


class TestEventStoreTimeFiltering:
    """Test time-based filtering of events."""
    
    def test_get_events_with_start_time(self):
        """get_events filters by start_time (inclusive)."""
        now = datetime(2025, 12, 21, 15, 0, 0, tzinfo=timezone.utc)
        
        event1 = create_event("DraftCreated", {"draft_id": "draft-1"}, now=now - timedelta(hours=2))
        event2 = create_event("DraftCreated", {"draft_id": "draft-2"}, now=now - timedelta(hours=1))
        event3 = create_event("DraftCreated", {"draft_id": "draft-3"}, now=now)
        
        EventStore.append(event1, "key-1")
        EventStore.append(event2, "key-2")
        EventStore.append(event3, "key-3")
        
        # Filter to events from (now - 1 hour) onwards
        events = EventStore.get_events(start_time=now - timedelta(hours=1))
        assert len(events) == 2  # event2 and event3
    
    def test_get_events_with_end_time(self):
        """get_events filters by end_time (inclusive)."""
        now = datetime(2025, 12, 21, 15, 0, 0, tzinfo=timezone.utc)
        
        event1 = create_event("DraftCreated", {"draft_id": "draft-1"}, now=now - timedelta(hours=2))
        event2 = create_event("DraftCreated", {"draft_id": "draft-2"}, now=now - timedelta(hours=1))
        event3 = create_event("DraftCreated", {"draft_id": "draft-3"}, now=now)
        
        EventStore.append(event1, "key-1")
        EventStore.append(event2, "key-2")
        EventStore.append(event3, "key-3")
        
        # Filter to events up to (now - 1 hour)
        events = EventStore.get_events(end_time=now - timedelta(hours=1))
        assert len(events) == 2  # event1 and event2
    
    def test_get_events_with_time_window(self):
        """get_events filters by both start_time and end_time."""
        now = datetime(2025, 12, 21, 15, 0, 0, tzinfo=timezone.utc)
        
        event1 = create_event("DraftCreated", {"draft_id": "draft-1"}, now=now - timedelta(hours=3))
        event2 = create_event("DraftCreated", {"draft_id": "draft-2"}, now=now - timedelta(hours=2))
        event3 = create_event("DraftCreated", {"draft_id": "draft-3"}, now=now - timedelta(hours=1))
        event4 = create_event("DraftCreated", {"draft_id": "draft-4"}, now=now)
        
        EventStore.append(event1, "key-1")
        EventStore.append(event2, "key-2")
        EventStore.append(event3, "key-3")
        EventStore.append(event4, "key-4")
        
        # Filter to events in window [now-2h, now-1h]
        events = EventStore.get_events(
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1)
        )
        assert len(events) == 2  # event2 and event3


class TestEventStoreTypeFiltering:
    """Test event type filtering."""
    
    def test_get_events_by_type(self):
        """get_events filters by event_type."""
        event1 = create_event("DraftCreated", {"draft_id": "draft-1"})
        event2 = create_event("DraftViewed", {"draft_id": "draft-1"})
        event3 = create_event("DraftViewed", {"draft_id": "draft-2"})
        event4 = create_event("SegmentAdded", {"segment_id": "seg-1"})
        
        EventStore.append(event1, "key-1")
        EventStore.append(event2, "key-2")
        EventStore.append(event3, "key-3")
        EventStore.append(event4, "key-4")
        
        # Filter to DraftViewed events only
        events = EventStore.get_events(event_type="DraftViewed")
        assert len(events) == 2
        assert all(e.event_type == "DraftViewed" for e in events)


class TestIdempotencyKeys:
    """Test idempotency key generation."""
    
    def test_generate_idempotency_key_draft_created(self):
        """Idempotency key for DraftCreated is deterministic."""
        key1 = generate_idempotency_key("DraftCreated", draft_id="draft-123")
        key2 = generate_idempotency_key("DraftCreated", draft_id="draft-123")
        
        assert key1 == key2
        assert "DraftCreated" in key1
        assert "draft-123" in key1
    
    def test_generate_idempotency_key_different_events(self):
        """Different event types produce different keys."""
        key1 = generate_idempotency_key("DraftCreated", draft_id="draft-123")
        key2 = generate_idempotency_key("DraftViewed", draft_id="draft-123", user_id="user-456")
        
        assert key1 != key2
    
    def test_generate_idempotency_key_sorted_params(self):
        """Idempotency key is stable regardless of parameter order."""
        key1 = generate_idempotency_key("Event", a="1", b="2", c="3")
        key2 = generate_idempotency_key("Event", c="3", a="1", b="2")
        
        assert key1 == key2


class TestEventDeterminism:
    """Test deterministic event creation."""
    
    def test_create_event_with_fixed_now(self):
        """create_event with fixed now produces deterministic timestamps."""
        fixed_now = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)
        
        event1 = create_event("DraftCreated", {"draft_id": "draft-123"}, now=fixed_now)
        event2 = create_event("DraftCreated", {"draft_id": "draft-123"}, now=fixed_now)
        
        assert event1.timestamp == event2.timestamp == fixed_now
    
    def test_create_event_without_now_uses_current_time(self):
        """create_event without now uses current UTC time."""
        before = datetime.now(timezone.utc)
        event = create_event("DraftCreated", {"draft_id": "draft-123"})
        after = datetime.now(timezone.utc)
        
        assert before <= event.timestamp <= after
        assert event.timestamp.tzinfo == timezone.utc


class TestEventSafety:
    """Test event safety guarantees."""
    
    def test_events_are_immutable(self):
        """Event models are frozen (immutable)."""
        event = create_event("DraftCreated", {"draft_id": "draft-123"})
        
        with pytest.raises(Exception):  # Pydantic ValidationError or similar
            event.event_type = "Modified"  # Should fail
    
    def test_event_store_does_not_expose_internal_state(self):
        """get_events returns copies, not references to internal store."""
        event = create_event("DraftCreated", {"draft_id": "draft-123"})
        EventStore.append(event, "key-1")
        
        events = EventStore.get_events()
        # Clear should not affect already-retrieved events
        EventStore.clear()
        
        assert len(events) == 1  # Retrieved events unaffected by clear
        assert EventStore.count() == 0  # Store is cleared
