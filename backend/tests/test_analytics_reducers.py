"""
backend/tests/test_analytics_reducers.py

Tests for analytics reducers (Phase 3.4).
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.features.analytics.reducers import (
    reduce_draft_analytics,
    reduce_user_analytics,
    reduce_leaderboard,
)
from backend.features.analytics.event_store import create_event, Event


@pytest.fixture
def fixed_now():
    """Fixed timestamp for deterministic testing."""
    return datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)


@pytest.fixture
def sample_draft_events(fixed_now):
    """Sample events for draft analytics testing."""
    return [
        create_event("DraftCreated", {"draft_id": "draft-1", "creator_id": "user-1"}, now=fixed_now - timedelta(hours=3)),
        create_event("SegmentAdded", {"draft_id": "draft-1", "segment_id": "seg-1", "contributor_id": "user-1"}, now=fixed_now - timedelta(hours=2)),
        create_event("SegmentAdded", {"draft_id": "draft-1", "segment_id": "seg-2", "contributor_id": "user-2"}, now=fixed_now - timedelta(hours=1)),
        create_event("RINGPassed", {"draft_id": "draft-1", "from_user_id": "user-1", "to_user_id": "user-2"}, now=fixed_now - timedelta(minutes=30)),
        create_event("DraftViewed", {"draft_id": "draft-1", "user_id": "user-3"}, now=fixed_now - timedelta(minutes=15)),
        create_event("DraftShared", {"draft_id": "draft-1", "user_id": "user-1"}, now=fixed_now - timedelta(minutes=5)),
    ]


class TestDraftAnalyticsDeterminism:
    """Test determinism of draft analytics reducer."""
    
    def test_same_events_same_now_produces_identical_output(self, sample_draft_events, fixed_now):
        """Same events + same now => byte-for-byte identical output."""
        result1 = reduce_draft_analytics("draft-1", sample_draft_events, now=fixed_now)
        result2 = reduce_draft_analytics("draft-1", sample_draft_events, now=fixed_now)
        
        assert result1.model_dump_json() == result2.model_dump_json()
        assert result1.computed_at == result2.computed_at == fixed_now
    
    def test_different_now_produces_same_metrics_different_computed_at(self, sample_draft_events, fixed_now):
        """Different now => same metrics, different computed_at."""
        result1 = reduce_draft_analytics("draft-1", sample_draft_events, now=fixed_now)
        result2 = reduce_draft_analytics("draft-1", sample_draft_events, now=fixed_now + timedelta(hours=1))
        
        assert result1.views == result2.views
        assert result1.shares == result2.shares
        assert result1.segments_count == result2.segments_count
        assert result1.computed_at != result2.computed_at


class TestDraftAnalyticsBounds:
    """Test bounds and constraints on draft analytics."""
    
    def test_views_and_shares_are_non_negative(self, sample_draft_events, fixed_now):
        """Views and shares are always >= 0."""
        result = reduce_draft_analytics("draft-1", sample_draft_events, now=fixed_now)
        
        assert result.views >= 0
        assert result.shares >= 0
    
    def test_contributors_count_at_least_one(self, fixed_now):
        """Contributors count is at least 1 (creator)."""
        events = [
            create_event("DraftCreated", {"draft_id": "draft-1", "creator_id": "user-1"}, now=fixed_now)
        ]
        
        result = reduce_draft_analytics("draft-1", events, now=fixed_now)
        
        assert result.contributors_count >= 1
    
    def test_empty_draft_has_minimum_values(self, fixed_now):
        """Draft with no events has sensible defaults."""
        result = reduce_draft_analytics("draft-nonexistent", [], now=fixed_now)
        
        assert result.views == 0
        assert result.shares == 0
        assert result.segments_count == 1  # Minimum 1
        assert result.contributors_count == 1  # Minimum 1
        assert result.ring_passes_count == 0


class TestDraftAnalyticsCalculations:
    """Test correctness of draft analytics calculations."""
    
    def test_views_count_draft_viewed_events(self, sample_draft_events, fixed_now):
        """Views count is number of DraftViewed events."""
        result = reduce_draft_analytics("draft-1", sample_draft_events, now=fixed_now)
        
        view_events = [e for e in sample_draft_events if e.event_type == "DraftViewed"]
        assert result.views == len(view_events) == 1
    
    def test_shares_count_draft_shared_events(self, sample_draft_events, fixed_now):
        """Shares count is number of DraftShared events."""
        result = reduce_draft_analytics("draft-1", sample_draft_events, now=fixed_now)
        
        share_events = [e for e in sample_draft_events if e.event_type == "DraftShared"]
        assert result.shares == len(share_events) == 1
    
    def test_segments_count_segment_added_events(self, sample_draft_events, fixed_now):
        """Segments count is number of SegmentAdded events."""
        result = reduce_draft_analytics("draft-1", sample_draft_events, now=fixed_now)
        
        segment_events = [e for e in sample_draft_events if e.event_type == "SegmentAdded"]
        assert result.segments_count == len(segment_events) == 2
    
    def test_contributors_count_unique_users(self, sample_draft_events, fixed_now):
        """Contributors count is number of unique contributors."""
        result = reduce_draft_analytics("draft-1", sample_draft_events, now=fixed_now)
        
        # user-1 (creator + segment), user-2 (segment) = 2 unique
        assert result.contributors_count == 2


class TestUserAnalyticsDeterminism:
    """Test determinism of user analytics reducer."""
    
    def test_same_events_same_now_produces_identical_output(self, sample_draft_events, fixed_now):
        """Same events + same now => byte-for-byte identical output."""
        result1 = reduce_user_analytics("user-1", sample_draft_events, now=fixed_now)
        result2 = reduce_user_analytics("user-1", sample_draft_events, now=fixed_now)
        
        assert result1.model_dump_json() == result2.model_dump_json()
        assert result1.computed_at == result2.computed_at == fixed_now
    
    def test_user_with_no_activity_has_zeros(self, fixed_now):
        """User with no events has all metrics = 0."""
        result = reduce_user_analytics("user-nonexistent", [], now=fixed_now)
        
        assert result.drafts_created == 0
        assert result.drafts_contributed == 0
        assert result.segments_written == 0
        assert result.rings_held_count == 0


class TestUserAnalyticsCalculations:
    """Test correctness of user analytics calculations."""
    
    def test_drafts_created_counts_draft_created_events(self, sample_draft_events, fixed_now):
        """drafts_created counts DraftCreated events by user."""
        result = reduce_user_analytics("user-1", sample_draft_events, now=fixed_now)
        
        created_events = [
            e for e in sample_draft_events
            if e.event_type == "DraftCreated" and e.data.get("creator_id") == "user-1"
        ]
        assert result.drafts_created == len(created_events) == 1
    
    def test_segments_written_counts_segment_added_events(self, sample_draft_events, fixed_now):
        """segments_written counts SegmentAdded events by user."""
        result = reduce_user_analytics("user-1", sample_draft_events, now=fixed_now)
        
        segment_events = [
            e for e in sample_draft_events
            if e.event_type == "SegmentAdded" and e.data.get("contributor_id") == "user-1"
        ]
        assert result.segments_written == len(segment_events) == 1
    
    def test_rings_held_count_received_ring_passes(self, sample_draft_events, fixed_now):
        """rings_held_count is number of RINGPassed events to user."""
        result = reduce_user_analytics("user-2", sample_draft_events, now=fixed_now)
        
        ring_received = [
            e for e in sample_draft_events
            if e.event_type == "RINGPassed" and e.data.get("to_user_id") == "user-2"
        ]
        assert result.rings_held_count == len(ring_received) == 1


class TestLeaderboardDeterminism:
    """Test determinism of leaderboard reducer."""
    
    def test_same_events_same_now_produces_identical_output(self, sample_draft_events, fixed_now):
        """Same events + same now => byte-for-byte identical leaderboard."""
        result1 = reduce_leaderboard("collaboration", sample_draft_events, now=fixed_now)
        result2 = reduce_leaderboard("collaboration", sample_draft_events, now=fixed_now)
        
        assert result1.model_dump_json() == result2.model_dump_json()
        assert result1.computed_at == result2.computed_at == fixed_now
    
    def test_leaderboard_entries_max_10(self, fixed_now):
        """Leaderboard returns max 10 entries."""
        # Create events for 15 users
        events = []
        for i in range(15):
            user_id = f"user-{i}"
            events.append(create_event("DraftCreated", {"draft_id": f"draft-{i}", "creator_id": user_id}, now=fixed_now))
            events.append(create_event("SegmentAdded", {"draft_id": f"draft-{i}", "segment_id": f"seg-{i}", "contributor_id": user_id}, now=fixed_now))
        
        result = reduce_leaderboard("collaboration", events, now=fixed_now)
        
        assert len(result.entries) <= 10
    
    def test_leaderboard_stable_sort_by_score_then_user_id(self, fixed_now):
        """Leaderboard sorts by score (desc), then user_id (asc) for ties."""
        events = [
            # user-a: 2 segments (score = 2×3 = 6)
            create_event("SegmentAdded", {"draft_id": "draft-1", "segment_id": "seg-1", "contributor_id": "user-a"}, now=fixed_now),
            create_event("SegmentAdded", {"draft_id": "draft-1", "segment_id": "seg-2", "contributor_id": "user-a"}, now=fixed_now),
            # user-b: 2 segments (score = 2×3 = 6) - SAME SCORE as user-a
            create_event("SegmentAdded", {"draft_id": "draft-2", "segment_id": "seg-3", "contributor_id": "user-b"}, now=fixed_now),
            create_event("SegmentAdded", {"draft_id": "draft-2", "segment_id": "seg-4", "contributor_id": "user-b"}, now=fixed_now),
            # user-c: 3 segments (score = 3×3 = 9)
            create_event("SegmentAdded", {"draft_id": "draft-3", "segment_id": "seg-5", "contributor_id": "user-c"}, now=fixed_now),
            create_event("SegmentAdded", {"draft_id": "draft-3", "segment_id": "seg-6", "contributor_id": "user-c"}, now=fixed_now),
            create_event("SegmentAdded", {"draft_id": "draft-3", "segment_id": "seg-7", "contributor_id": "user-c"}, now=fixed_now),
        ]
        
        result = reduce_leaderboard("collaboration", events, now=fixed_now)
        
        # Expected order: user-c (9), user-a (6, lower user_id), user-b (6)
        assert result.entries[0].user_id == "user-c"
        assert result.entries[1].user_id == "user-a"  # Tie-breaker: user-a < user-b
        assert result.entries[2].user_id == "user-b"


class TestLeaderboardSafety:
    """Test leaderboard safety guarantees."""
    
    def test_leaderboard_entries_have_no_sensitive_fields(self, sample_draft_events, fixed_now):
        """Leaderboard entries never include token_hash, passwords, secrets."""
        result = reduce_leaderboard("collaboration", sample_draft_events, now=fixed_now)
        
        response_str = result.model_dump_json()
        
        assert "token_hash" not in response_str
        assert "password" not in response_str
        assert "secret" not in response_str
        assert "email" not in response_str


class TestLeaderboardMessages:
    """Test leaderboard message content."""
    
    def test_leaderboard_message_is_never_comparative(self, sample_draft_events, fixed_now):
        """Leaderboard message never uses comparative or shame language."""
        result = reduce_leaderboard("collaboration", sample_draft_events, now=fixed_now)
        
        forbidden_phrases = [
            "you're behind",
            "catch up",
            "falling behind",
            "ahead of",
            "losing to",
            "better than",
            "worse than",
        ]
        
        message_lower = result.message.lower()
        for phrase in forbidden_phrases:
            assert phrase not in message_lower, f"Forbidden phrase '{phrase}' found in message"
    
    def test_leaderboard_insights_are_supportive(self, sample_draft_events, fixed_now):
        """All leaderboard insights are supportive, never shaming."""
        result = reduce_leaderboard("collaboration", sample_draft_events, now=fixed_now)
        
        forbidden_phrases = [
            "you're behind",
            "catch up",
            "do better",
            "not good enough",
            "falling",
        ]
        
        for entry in result.entries:
            insight_lower = entry.insight.lower()
            for phrase in forbidden_phrases:
                assert phrase not in insight_lower, f"Forbidden phrase '{phrase}' found in insight"


class TestLeaderboardMetrics:
    """Test leaderboard metric calculations."""
    
    def test_collaboration_metric_formula(self, fixed_now):
        """Collaboration = segments×3 + rings×2 + drafts_contributed."""
        events = [
            create_event("DraftCreated", {"draft_id": "draft-1", "creator_id": "user-1"}, now=fixed_now),
            create_event("SegmentAdded", {"draft_id": "draft-1", "segment_id": "seg-1", "contributor_id": "user-1"}, now=fixed_now),
            create_event("SegmentAdded", {"draft_id": "draft-1", "segment_id": "seg-2", "contributor_id": "user-1"}, now=fixed_now),
            create_event("RINGPassed", {"draft_id": "draft-1", "from_user_id": "user-2", "to_user_id": "user-1"}, now=fixed_now),
            create_event("SegmentAdded", {"draft_id": "draft-2", "segment_id": "seg-3", "contributor_id": "user-1"}, now=fixed_now),
        ]
        
        result = reduce_leaderboard("collaboration", events, now=fixed_now)
        
        # user-1: 3 segments (×3=9) + 1 ring (×2=2) + 1 draft_contributed = 12
        assert result.entries[0].metric_value == 12
    
    def test_consistency_metric_formula(self, fixed_now):
        """Consistency = drafts_created×5 + drafts_contributed×2."""
        events = [
            create_event("DraftCreated", {"draft_id": "draft-1", "creator_id": "user-1"}, now=fixed_now),
            create_event("DraftCreated", {"draft_id": "draft-2", "creator_id": "user-1"}, now=fixed_now),
            create_event("SegmentAdded", {"draft_id": "draft-3", "segment_id": "seg-1", "contributor_id": "user-1"}, now=fixed_now),
        ]
        
        result = reduce_leaderboard("consistency", events, now=fixed_now)
        
        # user-1: 2 drafts_created (×5=10) + 1 draft_contributed (×2=2) = 12
        assert result.entries[0].metric_value == 12
