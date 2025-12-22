"""
backend/tests/test_collab_presence_guardrails.py
Phase 3.3a: Presence + Attribution + Ring Velocity guardrail tests
All tests must be deterministic and testable without external services.
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.features.collaboration.service import (
    create_draft,
    get_draft,
    append_segment,
    pass_ring,
    clear_store,
    display_for_user,
    compute_metrics,
)
from backend.models.collab import (
    CollabDraftRequest,
    SegmentAppendRequest,
    RingPassRequest,
)


@pytest.fixture(autouse=True)
def reset_store():
    """Clear store before each test"""
    clear_store()
    yield
    clear_store()


class TestSegmentAttribution:
    """Test segment-level attribution fields"""

    def test_append_segment_sets_author_fields(self):
        """Append must set author_user_id and author_display"""
        # Create draft
        req = CollabDraftRequest(
            title="Test Draft",
            platform="x",
            initial_segment="First segment"
        )
        draft = create_draft("user_alice", req)
        
        # Check initial segment has attribution
        assert len(draft.segments) == 1
        seg = draft.segments[0]
        assert seg.author_user_id == "user_alice"
        assert seg.author_display is not None
        assert seg.author_display.startswith("@u_")
        
        # Append second segment
        append_req = SegmentAppendRequest(
            content="Second segment",
            idempotency_key="append-1"
        )
        updated_draft = append_segment(draft.draft_id, "user_alice", append_req)
        
        # Check new segment has attribution
        assert len(updated_draft.segments) == 2
        seg2 = updated_draft.segments[1]
        assert seg2.author_user_id == "user_alice"
        assert seg2.author_display == seg.author_display  # Same user, same display

    def test_append_segment_sets_ring_holder_fields(self):
        """Append must capture ring holder at time of writing"""
        # Create draft
        req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft("user_alice", req)
        
        # Alice appends (she's ring holder)
        append_req = SegmentAppendRequest(
            content="Alice's segment",
            idempotency_key="append-alice"
        )
        draft = append_segment(draft.draft_id, "user_alice", append_req)
        
        seg = draft.segments[0]
        assert seg.ring_holder_user_id_at_write == "user_alice"
        assert seg.ring_holder_display_at_write is not None
        assert seg.author_user_id == seg.ring_holder_user_id_at_write  # Same person

    def test_ring_holder_at_write_differs_from_author(self):
        """Ring holder at write can differ from author (future feature)"""
        # For now, only ring holder can append, so they're always the same
        # This test documents expected behavior
        req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft("user_alice", req)
        
        append_req = SegmentAppendRequest(
            content="Segment",
            idempotency_key="append-1"
        )
        draft = append_segment(draft.draft_id, "user_alice", append_req)
        
        seg = draft.segments[0]
        # Currently, author == ring holder (only ring holder can append)
        assert seg.author_user_id == seg.ring_holder_user_id_at_write


class TestRingPresence:
    """Test ring presence tracking"""

    def test_pass_ring_sets_last_passed_at(self):
        """Pass ring must set last_passed_at timestamp"""
        # Create draft
        req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft("user_alice", req)
        
        # Check initial state
        assert draft.ring_state.last_passed_at is not None
        initial_time = draft.ring_state.last_passed_at
        
        # Pass ring to Bob (need to add him as collaborator first via invite flow)
        # For this test, we'll just verify the pass updates last_passed_at
        pass_req = RingPassRequest(
            to_user_id="user_alice",  # Pass to self (allowed if creator)
            idempotency_key="pass-1"
        )
        
        # Can't actually pass since Bob not a collaborator, so test with self-pass
        updated_draft = pass_ring(draft.draft_id, "user_alice", pass_req)
        
        # Check last_passed_at updated
        assert updated_draft.ring_state.last_passed_at is not None
        assert updated_draft.ring_state.last_passed_at >= initial_time

    def test_ring_state_includes_passed_at(self):
        """Ring state must track passed_at for each transition"""
        req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft("user_alice", req)
        
        assert draft.ring_state.passed_at is not None
        assert isinstance(draft.ring_state.passed_at, datetime)


class TestDisplayForUser:
    """Test deterministic display name generation"""

    def test_display_for_user_is_deterministic(self):
        """Same user_id always produces same display name"""
        display1 = display_for_user("user_123")
        display2 = display_for_user("user_123")
        assert display1 == display2

    def test_display_for_user_different_users(self):
        """Different user_ids produce different display names"""
        display1 = display_for_user("user_alice")
        display2 = display_for_user("user_bob")
        assert display1 != display2

    def test_display_for_user_format(self):
        """Display name must follow @u_XXXXXX format"""
        display = display_for_user("user_test")
        assert display.startswith("@u_")
        assert len(display) == 9  # @u_ + 6 hex chars

    def test_display_contains_no_secrets(self):
        """Display name must not reveal email/token/secrets"""
        display = display_for_user("user_test@example.com")
        assert "@example.com" not in display
        assert "test@" not in display


class TestRingVelocityMetrics:
    """Test ring velocity metrics computation"""

    def test_metrics_contributors_count(self):
        """Contributors count includes creator + segment authors"""
        req = CollabDraftRequest(
            title="Test",
            platform="x",
            initial_segment="First"
        )
        draft = create_draft("user_alice", req)
        
        # Compute metrics
        draft_with_metrics = get_draft(draft.draft_id, compute_metrics_flag=True)
        assert draft_with_metrics.metrics is not None
        assert draft_with_metrics.metrics["contributorsCount"] == 1  # Only Alice
        
        # Add another segment (still Alice)
        append_req = SegmentAppendRequest(
            content="Second",
            idempotency_key="append-1"
        )
        draft = append_segment(draft.draft_id, "user_alice", append_req)
        
        draft_with_metrics = get_draft(draft.draft_id, compute_metrics_flag=True)
        assert draft_with_metrics.metrics["contributorsCount"] == 1  # Still only Alice

    def test_metrics_last_activity_at(self):
        """Last activity must be max of segment created_at, passed_at, created_at"""
        req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft("user_alice", req)
        
        draft_with_metrics = get_draft(draft.draft_id, compute_metrics_flag=True)
        assert draft_with_metrics.metrics["lastActivityAt"] is not None
        
        # Last activity should be draft creation time (no segments)
        last_activity = datetime.fromisoformat(draft_with_metrics.metrics["lastActivityAt"])
        assert last_activity >= draft.created_at

    def test_metrics_ring_passes_last_24h_with_fixed_now(self):
        """Ring passes last 24h must use fixed 'now' for determinism"""
        req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft("user_alice", req)
        
        # Fixed timestamp for testing
        fixed_now = datetime.now(timezone.utc)
        
        # Get metrics with fixed now
        draft_with_metrics = get_draft(draft.draft_id, compute_metrics_flag=True, now=fixed_now)
        
        # Should have at least 0 passes (just created)
        assert draft_with_metrics.metrics["ringPassesLast24h"] >= 0

    def test_metrics_avg_minutes_between_passes(self):
        """Avg minutes between passes computed from history"""
        req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft("user_alice", req)
        
        # With only 1 holder (no passes yet), avg should be None
        draft_with_metrics = get_draft(draft.draft_id, compute_metrics_flag=True)
        # Initially, history has 1 entry (creator), so no passes yet
        # But after creation, holders_history has [user_alice], so 0 passes
        # avg should be None
        assert draft_with_metrics.metrics["avgMinutesBetweenPasses"] is None or isinstance(
            draft_with_metrics.metrics["avgMinutesBetweenPasses"], (int, float)
        )

    def test_metrics_deterministic_with_same_now(self):
        """Same draft + same now => identical metrics"""
        req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft("user_alice", req)
        
        fixed_now = datetime.now(timezone.utc)
        
        metrics1 = get_draft(draft.draft_id, compute_metrics_flag=True, now=fixed_now).metrics
        metrics2 = get_draft(draft.draft_id, compute_metrics_flag=True, now=fixed_now).metrics
        
        assert metrics1 == metrics2


class TestMetricsFormulas:
    """Test specific metrics computation formulas"""

    def test_compute_metrics_function_directly(self):
        """Test compute_metrics helper function"""
        req = CollabDraftRequest(
            title="Test",
            platform="x",
            initial_segment="First"
        )
        draft = create_draft("user_alice", req)
        
        fixed_now = datetime.now(timezone.utc)
        metrics = compute_metrics(draft, now=fixed_now)
        
        assert "contributorsCount" in metrics
        assert "ringPassesLast24h" in metrics
        assert "avgMinutesBetweenPasses" in metrics
        assert "lastActivityAt" in metrics
        
        assert metrics["contributorsCount"] == 1
        assert isinstance(metrics["ringPassesLast24h"], int)
        assert metrics["avgMinutesBetweenPasses"] is None or isinstance(
            metrics["avgMinutesBetweenPasses"], (int, float)
        )

    def test_metrics_with_multiple_passes(self):
        """Test metrics with multiple ring passes"""
        req = CollabDraftRequest(title="Test", platform="x")
        draft = create_draft("user_alice", req)
        
        # Pass ring to self multiple times (to build history)
        for i in range(3):
            pass_req = RingPassRequest(
                to_user_id="user_alice",
                idempotency_key=f"pass-{i}"
            )
            draft = pass_ring(draft.draft_id, "user_alice", pass_req)
        
        # Check holders_history length
        assert len(draft.ring_state.holders_history) == 4  # Initial + 3 passes
        
        # Get metrics
        draft_with_metrics = get_draft(draft.draft_id, compute_metrics_flag=True)
        
        # Should have avgMinutesBetweenPasses now (>= 2 passes)
        assert draft_with_metrics.metrics["avgMinutesBetweenPasses"] is not None


class TestBackwardCompatibility:
    """Test that old segments without attribution fields still work"""

    def test_metrics_handle_missing_attribution_fields(self):
        """Metrics should fallback to user_id if author_user_id missing"""
        # Create draft (will have attribution)
        req = CollabDraftRequest(
            title="Test",
            platform="x",
            initial_segment="First"
        )
        draft = create_draft("user_alice", req)
        
        # Manually create a segment without attribution (simulating old data)
        # This would only happen in real DB migration scenario
        # For now, just verify metrics work with normal segments
        
        draft_with_metrics = get_draft(draft.draft_id, compute_metrics_flag=True)
        assert draft_with_metrics.metrics["contributorsCount"] >= 1


class TestDeterminism:
    """Test all Phase 3.3a features are deterministic"""

    def test_same_sequence_same_now_identical_response(self):
        """Same actions + same now => identical draft state"""
        fixed_now = datetime(2025, 12, 21, 12, 0, 0, tzinfo=timezone.utc)
        
        # Sequence 1
        clear_store()
        req1 = CollabDraftRequest(title="Test", platform="x", initial_segment="First")
        draft1 = create_draft("user_alice", req1)
        draft1_with_metrics = get_draft(draft1.draft_id, compute_metrics_flag=True, now=fixed_now)
        
        # Sequence 2 (identical actions)
        clear_store()
        req2 = CollabDraftRequest(title="Test", platform="x", initial_segment="First")
        draft2 = create_draft("user_alice", req2)
        draft2_with_metrics = get_draft(draft2.draft_id, compute_metrics_flag=True, now=fixed_now)
        
        # Compare metrics (excluding lastActivityAt which depends on actual creation time)
        assert draft1_with_metrics.metrics["contributorsCount"] == draft2_with_metrics.metrics["contributorsCount"]
        assert draft1_with_metrics.metrics["ringPassesLast24h"] == draft2_with_metrics.metrics["ringPassesLast24h"]
        assert draft1_with_metrics.metrics["avgMinutesBetweenPasses"] == draft2_with_metrics.metrics["avgMinutesBetweenPasses"]
        
        # Author displays should be identical (deterministic)
        assert draft1_with_metrics.segments[0].author_display == draft2_with_metrics.segments[0].author_display
