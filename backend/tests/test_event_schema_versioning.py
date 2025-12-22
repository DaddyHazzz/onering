"""Event schema versioning tests (Phase 4.0)."""
import pytest
from datetime import datetime, timezone
from backend.features.analytics.event_store import Event, EventStore
from backend.features.analytics.reducers import reduce_draft_analytics
from backend.core.errors import ValidationError


def test_unknown_schema_version_rejected():
    EventStore.clear()
    # Create an event with schema_version 99
    e = Event(event_type="DraftCreated", timestamp=datetime.now(timezone.utc), data={"draft_id": "d1", "creator_id": "u1"}, schema_version=99)
    EventStore.append(e, "k1")
    with pytest.raises(ValidationError):
        reduce_draft_analytics("d1", EventStore.get_events(), now=datetime.now(timezone.utc))
