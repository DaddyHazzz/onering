"""
backend/tests/test_event_store_pg.py

Tests for PostgreSQL-backed event store (Phase 3.5).

Tests cover:
- Append-only semantics
- Idempotency enforcement
- Deterministic ordering
- Persistence across restarts
- Reducer compatibility
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.features.analytics.event_store_pg import PostgresEventStore
from backend.features.analytics.event_store import Event, create_event
from backend.core.database import create_all_tables, drop_all_tables


@pytest.fixture(scope="function")
def clean_db():
    """Ensure clean database for each test."""
    # Setup: create tables
    create_all_tables()
    
    # Clear any existing data
    store = PostgresEventStore()
    store.clear()
    
    yield store
    
    # Teardown: clear data
    store.clear()


def test_append_event(clean_db):
    """Test basic event appending."""
    store = clean_db
    
    # Create event
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event = Event(
        event_type="DraftCreated",
        timestamp=now,
        data={"draft_id": "draft-123", "creator_id": "user-456"}
    )
    
    # Append event
    result = store.append(event, "test-key-1")
    
    assert result is True, "First append should succeed"
    assert store.count() == 1, "Store should have 1 event"


def test_idempotency_enforcement(clean_db):
    """Test that duplicate idempotency keys are rejected."""
    store = clean_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event = Event(
        event_type="DraftCreated",
        timestamp=now,
        data={"draft_id": "draft-123"}
    )
    
    # First append should succeed
    result1 = store.append(event, "duplicate-key")
    assert result1 is True, "First append should succeed"
    
    # Second append with same key should fail
    result2 = store.append(event, "duplicate-key")
    assert result2 is False, "Duplicate key should be rejected"
    
    # Store should still have only 1 event
    assert store.count() == 1, "Store should have exactly 1 event"


def test_get_events_returns_copies(clean_db):
    """Test that get_events returns copies, not references."""
    store = clean_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event = Event(
        event_type="DraftViewed",
        timestamp=now,
        data={"draft_id": "draft-123", "user_id": "user-456"}
    )
    
    store.append(event, "key-1")
    
    # Get events twice
    events1 = store.get_events()
    events2 = store.get_events()
    
    # Should be equal but not the same object
    assert len(events1) == len(events2) == 1
    assert events1[0].event_type == events2[0].event_type
    assert events1[0] is not events2[0], "Should return copies, not references"


def test_deterministic_ordering(clean_db):
    """Test that events are returned in deterministic order."""
    store = clean_db
    
    base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Add events out of order
    events_to_add = [
        (Event(event_type="Event3", timestamp=base_time + timedelta(seconds=3), data={"seq": 3}), "key-3"),
        (Event(event_type="Event1", timestamp=base_time + timedelta(seconds=1), data={"seq": 1}), "key-1"),
        (Event(event_type="Event2", timestamp=base_time + timedelta(seconds=2), data={"seq": 2}), "key-2"),
    ]
    
    for event, key in events_to_add:
        store.append(event, key)
    
    # Retrieve events
    retrieved = store.get_events()
    
    # Should be ordered by timestamp
    assert len(retrieved) == 3
    assert retrieved[0].data["seq"] == 1
    assert retrieved[1].data["seq"] == 2
    assert retrieved[2].data["seq"] == 3


def test_time_window_filtering(clean_db):
    """Test filtering events by time window."""
    store = clean_db
    
    base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Add events at different times
    for i in range(5):
        event = Event(
            event_type="TestEvent",
            timestamp=base_time + timedelta(hours=i),
            data={"hour": i}
        )
        store.append(event, f"key-{i}")
    
    # Query with time window (hours 1-3)
    start_time = base_time + timedelta(hours=1)
    end_time = base_time + timedelta(hours=3)
    
    filtered = store.get_events(start_time=start_time, end_time=end_time)
    
    assert len(filtered) == 3
    assert filtered[0].data["hour"] == 1
    assert filtered[1].data["hour"] == 2
    assert filtered[2].data["hour"] == 3


def test_event_type_filtering(clean_db):
    """Test filtering events by type."""
    store = clean_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Add different event types
    event_types = ["DraftCreated", "DraftViewed", "DraftCreated", "SegmentAdded"]
    for i, event_type in enumerate(event_types):
        event = Event(
            event_type=event_type,
            timestamp=now + timedelta(seconds=i),
            data={"index": i}
        )
        store.append(event, f"key-{i}")
    
    # Query for DraftCreated events only
    filtered = store.get_events(event_type="DraftCreated")
    
    assert len(filtered) == 2
    assert all(e.event_type == "DraftCreated" for e in filtered)
    assert filtered[0].data["index"] == 0
    assert filtered[1].data["index"] == 2


def test_persistence_simulation(clean_db):
    """Test that events persist (simulated by clearing and re-querying)."""
    store = clean_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Add event
    event = Event(
        event_type="DraftCreated",
        timestamp=now,
        data={"draft_id": "draft-persist"}
    )
    store.append(event, "persist-key")
    
    # Create new store instance (simulates restart)
    new_store = PostgresEventStore()
    
    # Should still have the event
    events = new_store.get_events()
    assert len(events) == 1
    assert events[0].event_type == "DraftCreated"
    assert events[0].data["draft_id"] == "draft-persist"


def test_clear_removes_all_events(clean_db):
    """Test that clear() removes all events."""
    store = clean_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Add multiple events
    for i in range(5):
        event = Event(
            event_type="TestEvent",
            timestamp=now + timedelta(seconds=i),
            data={"index": i}
        )
        store.append(event, f"key-{i}")
    
    assert store.count() == 5
    
    # Clear
    store.clear()
    
    # Should be empty
    assert store.count() == 0
    assert len(store.get_events()) == 0


def test_check_idempotency(clean_db):
    """Test idempotency checking."""
    store = clean_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event = Event(
        event_type="DraftCreated",
        timestamp=now,
        data={"draft_id": "draft-123"}
    )
    
    # Key should not exist initially
    assert store.check_idempotency("test-key") is False
    
    # Append event
    store.append(event, "test-key")
    
    # Key should exist now
    assert store.check_idempotency("test-key") is True


def test_same_timestamp_different_events(clean_db):
    """Test that events with same timestamp maintain order by ID."""
    store = clean_db
    
    same_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Add multiple events with same timestamp
    for i in range(3):
        event = Event(
            event_type="TestEvent",
            timestamp=same_time,
            data={"order": i}
        )
        store.append(event, f"key-{i}")
    
    # Retrieve events
    retrieved = store.get_events()
    
    # Should maintain insertion order (via ID)
    assert len(retrieved) == 3
    assert retrieved[0].data["order"] == 0
    assert retrieved[1].data["order"] == 1
    assert retrieved[2].data["order"] == 2


def test_empty_data_payload(clean_db):
    """Test that events with empty data work correctly."""
    store = clean_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event = Event(
        event_type="SimpleEvent",
        timestamp=now,
        data={}
    )
    
    store.append(event, "empty-key")
    
    retrieved = store.get_events()
    assert len(retrieved) == 1
    assert retrieved[0].data == {}


def test_combined_filters(clean_db):
    """Test combining time window and event type filters."""
    store = clean_db
    
    base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Add various events
    test_data = [
        ("DraftCreated", 0),
        ("DraftViewed", 1),
        ("DraftCreated", 2),
        ("DraftViewed", 3),
        ("DraftCreated", 4),
    ]
    
    for event_type, hour in test_data:
        event = Event(
            event_type=event_type,
            timestamp=base_time + timedelta(hours=hour),
            data={"hour": hour}
        )
        store.append(event, f"key-{hour}")
    
    # Query for DraftCreated events in hours 1-4
    start_time = base_time + timedelta(hours=1)
    end_time = base_time + timedelta(hours=4)
    
    filtered = store.get_events(
        start_time=start_time,
        end_time=end_time,
        event_type="DraftCreated"
    )
    
    # Should only get DraftCreated events at hours 2 and 4
    assert len(filtered) == 2
    assert filtered[0].data["hour"] == 2
    assert filtered[1].data["hour"] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
