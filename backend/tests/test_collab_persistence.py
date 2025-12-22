"""
backend/tests/test_collab_persistence.py

Tests for PostgreSQL-backed collaboration draft persistence (Phase 3.5).

Covers:
- Draft creation and retrieval
- Segment appending with deterministic ordering
- Collaborator management
- Ring pass tracking
- Persistence across restarts
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.features.collaboration.persistence import DraftPersistence
from backend.models.collab import (
    CollabDraft,
    DraftSegment,
    RingState,
    DraftStatus,
)
from backend.core.database import create_all_tables


@pytest.fixture(scope="function")
def clean_collab_db():
    """Ensure clean database for each test."""
    from backend.core.database import get_db_session, idempotency_keys
    from sqlalchemy import delete
    
    # Setup: create tables
    create_all_tables()
    
    # Clear any existing data
    persistence = DraftPersistence()
    persistence.clear_all()
    
    # Also clear all idempotency keys
    with get_db_session() as session:
        session.execute(delete(idempotency_keys))
        session.commit()
    
    yield persistence
    
    # Teardown: clear data
    persistence.clear_all()
    with get_db_session() as session:
        session.execute(delete(idempotency_keys))
        session.commit()


def test_create_and_retrieve_draft(clean_collab_db):
    """Test basic draft creation and retrieval."""
    persistence = clean_collab_db
    
    # Create draft
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ring_state = RingState(
        draft_id="draft-123",
        current_holder_id="user-1",
        holders_history=["user-1"],
        passed_at=now,
        last_passed_at=now,
    )
    
    draft = CollabDraft(
        draft_id="draft-123",
        creator_id="user-1",
        title="Test Draft",
        platform="X",
        status=DraftStatus.ACTIVE,
        segments=[],
        ring_state=ring_state,
        created_at=now,
        updated_at=now,
    )
    
    # Persist
    result = persistence.create_draft(draft)
    assert result is True, "First create should succeed"
    
    # Retrieve
    retrieved = persistence.get_draft("draft-123")
    assert retrieved is not None
    assert retrieved.draft_id == "draft-123"
    assert retrieved.creator_id == "user-1"
    assert retrieved.title == "Test Draft"
    assert retrieved.platform == "X"
    assert retrieved.status == DraftStatus.ACTIVE


def test_duplicate_draft_creation(clean_collab_db):
    """Test that duplicate draft IDs are rejected."""
    persistence = clean_collab_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ring_state = RingState(
        draft_id="draft-dup",
        current_holder_id="user-1",
        holders_history=["user-1"],
        passed_at=now,
        last_passed_at=now,
    )
    
    draft = CollabDraft(
        draft_id="draft-dup",
        creator_id="user-1",
        title="Duplicate Test",
        platform="X",
        status=DraftStatus.ACTIVE,
        segments=[],
        ring_state=ring_state,
        created_at=now,
        updated_at=now,
    )
    
    # First create
    result1 = persistence.create_draft(draft)
    assert result1 is True
    
    # Second create (should fail)
    result2 = persistence.create_draft(draft)
    assert result2 is False


def test_append_segments_deterministic_ordering(clean_collab_db):
    """Test that segments maintain deterministic order."""
    persistence = clean_collab_db
    
    # Create draft
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ring_state = RingState(
        draft_id="draft-segments",
        current_holder_id="user-1",
        holders_history=["user-1"],
        passed_at=now,
        last_passed_at=now,
    )
    
    draft = CollabDraft(
        draft_id="draft-segments",
        creator_id="user-1",
        title="Segment Test",
        platform="X",
        status=DraftStatus.ACTIVE,
        segments=[],
        ring_state=ring_state,
        created_at=now,
        updated_at=now,
    )
    
    persistence.create_draft(draft)
    
    # Add segments in order
    for i in range(3):
        segment = DraftSegment(
            segment_id=f"seg-{i}",
            draft_id="draft-segments",
            user_id="user-1",
            content=f"Content {i}",
            created_at=now + timedelta(seconds=i),
            segment_order=i,
            author_user_id="user-1",
            author_display="@user1",
            ring_holder_user_id_at_write="user-1",
            ring_holder_display_at_write="@user1",
        )
        persistence.append_segment("draft-segments", segment)
    
    # Retrieve and verify order
    retrieved = persistence.get_draft("draft-segments")
    assert len(retrieved.segments) == 3
    assert retrieved.segments[0].content == "Content 0"
    assert retrieved.segments[1].content == "Content 1"
    assert retrieved.segments[2].content == "Content 2"


def test_list_drafts_by_user(clean_collab_db):
    """Test listing drafts by user involvement."""
    persistence = clean_collab_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Create draft by user-1
    ring_state1 = RingState(
        draft_id="draft-user1",
        current_holder_id="user-1",
        holders_history=["user-1"],
        passed_at=now,
        last_passed_at=now,
    )
    
    draft1 = CollabDraft(
        draft_id="draft-user1",
        creator_id="user-1",
        title="User 1 Draft",
        platform="X",
        status=DraftStatus.ACTIVE,
        segments=[],
        ring_state=ring_state1,
        created_at=now,
        updated_at=now,
    )
    
    persistence.create_draft(draft1)
    
    # Create draft by user-2
    ring_state2 = RingState(
        draft_id="draft-user2",
        current_holder_id="user-2",
        holders_history=["user-2"],
        passed_at=now,
        last_passed_at=now,
    )
    
    draft2 = CollabDraft(
        draft_id="draft-user2",
        creator_id="user-2",
        title="User 2 Draft",
        platform="X",
        status=DraftStatus.ACTIVE,
        segments=[],
        ring_state=ring_state2,
        created_at=now,
        updated_at=now,
    )
    
    persistence.create_draft(draft2)
    
    # Add segment by user-1 to draft2
    segment = DraftSegment(
        segment_id="seg-cross",
        draft_id="draft-user2",
        user_id="user-1",
        content="User 1 contributing",
        created_at=now,
        segment_order=0,
        author_user_id="user-1",
        author_display="@user1",
        ring_holder_user_id_at_write="user-2",
        ring_holder_display_at_write="@user2",
    )
    persistence.append_segment("draft-user2", segment)
    
    # List drafts for user-1 (should see both)
    user1_drafts = persistence.list_drafts_by_user("user-1")
    draft_ids = [d.draft_id for d in user1_drafts]
    assert "draft-user1" in draft_ids
    assert "draft-user2" in draft_ids  # Because user-1 added a segment
    
    # List drafts for user-2 (should see only draft-user2)
    user2_drafts = persistence.list_drafts_by_user("user-2")
    user2_ids = [d.draft_id for d in user2_drafts]
    assert "draft-user2" in user2_ids
    assert "draft-user1" not in user2_ids


def test_ring_pass_tracking(clean_collab_db):
    """Test that ring passes are tracked with deterministic ordering."""
    persistence = clean_collab_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    
    # Create draft with initial holder
    ring_state = RingState(
        draft_id="draft-ring",
        current_holder_id="user-1",
        holders_history=["user-1"],
        passed_at=now,
        last_passed_at=now,
    )
    
    draft = CollabDraft(
        draft_id="draft-ring",
        creator_id="user-1",
        title="Ring Pass Test",
        platform="X",
        status=DraftStatus.ACTIVE,
        segments=[],
        ring_state=ring_state,
        created_at=now,
        updated_at=now,
    )
    
    persistence.create_draft(draft)
    
    # Pass ring: user-1 -> user-2
    persistence.pass_ring("draft-ring", "user-1", "user-2", now + timedelta(minutes=1))
    
    # Pass ring: user-2 -> user-3
    persistence.pass_ring("draft-ring", "user-2", "user-3", now + timedelta(minutes=2))
    
    # Retrieve and verify history
    retrieved = persistence.get_draft("draft-ring")
    
    # History includes initial holder + passes
    # Ring passes: user-1 (initial) -> user-2 -> user-3
    # holders_history should be: [user-1, user-2, user-3]
    assert len(retrieved.ring_state.holders_history) == 3
    assert retrieved.ring_state.holders_history[0] == "user-1"  # Initial
    assert retrieved.ring_state.holders_history[1] == "user-2"
    assert retrieved.ring_state.holders_history[2] == "user-3"
    assert retrieved.ring_state.current_holder_id == "user-3"


def test_persistence_across_restart_simulation(clean_collab_db):
    """Test that data persists across 'restarts' (new persistence instances)."""
    # First instance creates draft
    persistence1 = DraftPersistence()
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ring_state = RingState(
        draft_id="draft-persist",
        current_holder_id="user-1",
        holders_history=["user-1"],
        passed_at=now,
        last_passed_at=now,
    )
    
    draft = CollabDraft(
        draft_id="draft-persist",
        creator_id="user-1",
        title="Persistence Test",
        platform="X",
        status=DraftStatus.ACTIVE,
        segments=[],
        ring_state=ring_state,
        created_at=now,
        updated_at=now,
    )
    
    persistence1.create_draft(draft)
    
    # Second instance (simulates restart) retrieves draft
    persistence2 = DraftPersistence()
    retrieved = persistence2.get_draft("draft-persist")
    
    assert retrieved is not None
    assert retrieved.draft_id == "draft-persist"
    assert retrieved.title == "Persistence Test"


def test_idempotency_keys(clean_collab_db):
    """Test idempotency key checking and recording."""
    persistence = clean_collab_db
    
    key = "test-idem-key-unique"
    
    # Should not exist initially
    assert persistence.check_idempotency(key) is False
    
    # Record it
    result = persistence.record_idempotency(key, scope="test")
    assert result is True
    
    # Should exist now
    assert persistence.check_idempotency(key) is True
    
    # Try to record again (should fail)
    result2 = persistence.record_idempotency(key, scope="test")
    assert result2 is False


def test_update_draft(clean_collab_db):
    """Test draft update functionality."""
    persistence = clean_collab_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ring_state = RingState(
        draft_id="draft-update",
        current_holder_id="user-1",
        holders_history=["user-1"],
        passed_at=now,
        last_passed_at=now,
    )
    
    draft = CollabDraft(
        draft_id="draft-update",
        creator_id="user-1",
        title="Original Title",
        platform="X",
        status=DraftStatus.ACTIVE,
        segments=[],
        ring_state=ring_state,
        created_at=now,
        updated_at=now,
    )
    
    persistence.create_draft(draft)
    
    # Update draft
    updated_draft = CollabDraft(
        draft_id="draft-update",
        creator_id="user-1",
        title="Original Title",
        platform="X",
        status=DraftStatus.COMPLETED,
        segments=[],
        ring_state=ring_state,
        created_at=now,
        updated_at=now + timedelta(hours=1),
    )
    
    result = persistence.update_draft(updated_draft)
    assert result is True
    
    # Retrieve and verify
    retrieved = persistence.get_draft("draft-update")
    assert retrieved.status == DraftStatus.COMPLETED


def test_clear_all(clean_collab_db):
    """Test that clear_all removes all data."""
    persistence = clean_collab_db
    
    now = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    ring_state = RingState(
        draft_id="draft-clear",
        current_holder_id="user-1",
        holders_history=["user-1"],
        passed_at=now,
        last_passed_at=now,
    )
    
    draft = CollabDraft(
        draft_id="draft-clear",
        creator_id="user-1",
        title="Clear Test",
        platform="X",
        status=DraftStatus.ACTIVE,
        segments=[],
        ring_state=ring_state,
        created_at=now,
        updated_at=now,
    )
    
    persistence.create_draft(draft)
    
    # Verify exists
    retrieved = persistence.get_draft("draft-clear")
    assert retrieved is not None
    
    # Clear all
    persistence.clear_all()
    
    # Should not exist anymore
    retrieved2 = persistence.get_draft("draft-clear")
    assert retrieved2 is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
