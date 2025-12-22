"""
Tests for usage accounting (Phase 4.1).
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from backend.features.usage.service import (
    emit_usage_event,
    get_usage_events,
    reduce_usage,
    get_usage_count,
)
from backend.features.collaboration.service import create_draft, append_segment
from backend.models.collab import CollabDraftRequest, SegmentAppendRequest
from backend.core.database import check_connection


# Skip all tests if no database connection
pytestmark = pytest.mark.skipif(
    not check_connection(),
    reason="Database not available"
)


def test_emit_usage_event():
    """Should emit usage event."""
    from backend.features.users.service import get_or_create_user
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    now = datetime.now(timezone.utc)
    
    event = emit_usage_event(
        user_id=user_id,
        usage_key="drafts.created",
        occurred_at=now,
        metadata={"draft_id": "draft-123"}
    )
    
    assert event.user_id == user_id
    assert event.usage_key == "drafts.created"
    assert event.occurred_at == now
    assert event.metadata["draft_id"] == "draft-123"


def test_get_usage_events():
    """Should retrieve usage events for user."""
    from backend.features.users.service import get_or_create_user
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    now = datetime.now(timezone.utc)
    
    # Emit 3 events
    emit_usage_event(user_id, "drafts.created", now)
    emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=1))
    emit_usage_event(user_id, "segments.appended", now + timedelta(seconds=2))
    
    # Get all events
    events = get_usage_events(user_id)
    assert len(events) >= 3


def test_get_usage_events_filtered_by_key():
    """Should filter events by usage key."""
    from backend.features.users.service import get_or_create_user
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    now = datetime.now(timezone.utc)
    
    emit_usage_event(user_id, "drafts.created", now)
    emit_usage_event(user_id, "segments.appended", now)
    
    draft_events = get_usage_events(user_id, usage_key="drafts.created")
    assert all(e.usage_key == "drafts.created" for e in draft_events)


def test_get_usage_events_time_window():
    """Should filter events by time window."""
    from backend.features.users.service import get_or_create_user
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    now = datetime.now(timezone.utc)
    
    emit_usage_event(user_id, "drafts.created", now - timedelta(days=10))
    emit_usage_event(user_id, "drafts.created", now - timedelta(days=5))
    emit_usage_event(user_id, "drafts.created", now)
    
    # Get events from last 7 days
    recent_events = get_usage_events(
        user_id,
        start_time=now - timedelta(days=7),
        end_time=now
    )
    
    assert len(recent_events) >= 2  # Should include -5 days and now


def test_reduce_usage():
    """Should reduce usage events to counts."""
    from backend.features.users.service import get_or_create_user
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    now = datetime.now(timezone.utc)
    
    # Emit events
    emit_usage_event(user_id, "drafts.created", now)
    emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=1))
    emit_usage_event(user_id, "segments.appended", now)
    
    # Reduce
    counts = reduce_usage(user_id, now=now + timedelta(seconds=2))
    
    assert counts["drafts.created"] >= 2
    assert counts["segments.appended"] >= 1


def test_reduce_usage_deterministic():
    """Same user + same now = same counts."""
    from backend.features.users.service import get_or_create_user
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    now = datetime.now(timezone.utc)
    
    emit_usage_event(user_id, "drafts.created", now)
    emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=1))
    
    counts1 = reduce_usage(user_id, now=now + timedelta(seconds=2))
    counts2 = reduce_usage(user_id, now=now + timedelta(seconds=2))
    
    assert counts1 == counts2


def test_reduce_usage_rolling_window():
    """Should support rolling window (e.g., last 30 days)."""
    from backend.features.users.service import get_or_create_user
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    now = datetime.now(timezone.utc)
    
    # Old event (outside window)
    emit_usage_event(user_id, "drafts.created", now - timedelta(days=40))
    # Recent events (inside window)
    emit_usage_event(user_id, "drafts.created", now - timedelta(days=10))
    emit_usage_event(user_id, "drafts.created", now)
    
    counts = reduce_usage(user_id, now=now, window_days=30)
    
    assert counts["drafts.created"] >= 2  # Should exclude the 40-day-old event


def test_get_usage_count():
    """Should get count for specific usage key."""
    from backend.features.users.service import get_or_create_user
    user = get_or_create_user(f"user-{uuid4()}")
    user_id = user.user_id
    now = datetime.now(timezone.utc)
    
    emit_usage_event(user_id, "drafts.created", now)
    emit_usage_event(user_id, "drafts.created", now + timedelta(seconds=1))
    
    count = get_usage_count(user_id, "drafts.created", now=now + timedelta(seconds=2))
    
    assert count >= 2


def test_draft_creation_emits_usage_event():
    """Creating draft should emit drafts.created event."""
    user_id = f"user-{uuid4()}"
    now = datetime.now(timezone.utc)
    
    # Create draft
    draft = create_draft(
        user_id,
        CollabDraftRequest(title="Test", platform="x", initial_segment="Hi")
    )
    
    # Check usage count
    count = get_usage_count(user_id, "drafts.created", now=now + timedelta(seconds=1))
    assert count >= 1


def test_segment_append_emits_usage_event():
    """Appending segment should emit segments.appended event."""
    user_id = f"user-{uuid4()}"
    now = datetime.now(timezone.utc)
    
    # Create draft
    draft = create_draft(
        user_id,
        CollabDraftRequest(title="Test", platform="x", initial_segment="Hi")
    )
    
    # Append segment
    append_segment(
        draft.draft_id,
        user_id,
        SegmentAppendRequest(content="More", idempotency_key=str(uuid4()))
    )
    
    # Check usage count
    count = get_usage_count(user_id, "segments.appended", now=now + timedelta(seconds=1))
    assert count >= 1


def test_usage_empty_for_new_user():
    """New user should have zero usage."""
    user_id = f"user-{uuid4()}"
    
    counts = reduce_usage(user_id)
    assert len(counts) == 0
