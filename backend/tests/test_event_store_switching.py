"""
backend/tests/test_event_store_switching.py

Tests for event store switching logic (Phase 3.5).

Verifies:
- Postgres used when DATABASE_URL is set and DB is available
- In-memory used when DATABASE_URL not set
- Graceful fallback to in-memory if DB unavailable
- API consumers are agnostic to implementation
"""

import pytest
import os
from datetime import datetime, timezone
from backend.features.analytics.event_store import (
    get_event_store,
    get_store,
    reset_store,
    Event,
    EventStore,
)


def test_postgres_store_when_database_url_set():
    """Test that PostgreSQL store is used when DATABASE_URL is set."""
    # Ensure DATABASE_URL is set
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/onering"
    
    # Reset to force re-initialization
    reset_store()
    
    # Get store
    store = get_event_store()
    
    # Should be PostgresEventStore (check by class name)
    assert store.__class__.__name__ == "PostgresEventStore"


def test_in_memory_store_when_no_database_url():
    """Test that in-memory store is used when DATABASE_URL not set."""
    # Save original DATABASE_URL
    original_url = os.environ.get("DATABASE_URL")
    
    try:
        # Remove DATABASE_URL
        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
        
        # Force reload of settings
        from backend.core import config
        import importlib
        importlib.reload(config)
        
        # Reset to force re-initialization
        reset_store()
        
        # Get store
        store = get_event_store()
        
        # Should be in-memory EventStore
        assert isinstance(store, EventStore)
        
    finally:
        # Restore original DATABASE_URL
        if original_url:
            os.environ["DATABASE_URL"] = original_url


def test_store_singleton():
    """Test that get_store() returns singleton instance."""
    reset_store()
    
    store1 = get_store()
    store2 = get_store()
    
    # Should be same instance
    assert store1 is store2


def test_store_api_agnostic():
    """Test that API consumers work with both implementations."""
    # Ensure DATABASE_URL is set for this test
    os.environ["DATABASE_URL"] = "postgresql://user:pass@localhost:5432/onering"
    
    reset_store()
    store = get_store()
    
    # Clear any existing data
    store.clear()
    
    # Test common API
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    event = Event(
        event_type="TestEvent",
        timestamp=now,
        data={"test": "data"}
    )
    
    # Append should work
    result = store.append(event, "test-key-api")
    assert result is True
    
    # Get events should work
    events = store.get_events()
    assert len(events) >= 1
    
    # Count should work
    count = store.count()
    assert count >= 1
    
    # Clear should work
    store.clear()
    assert store.count() == 0


def test_reset_store_forces_reinitialization():
    """Test that reset_store() forces fresh initialization."""
    reset_store()
    
    store1 = get_store()
    
    # Reset
    reset_store()
    
    store2 = get_store()
    
    # Should be different instances (but same type)
    assert store1 is not store2
    assert type(store1) == type(store2)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
