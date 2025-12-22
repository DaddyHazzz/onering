"""
backend/tests/test_analytics.py
Phase 3.4 analytics tests: determinism, safety, bounds, ordering.
"""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.models.analytics import DraftAnalytics, UserAnalytics, LeaderboardEntry, LeaderboardResponse
from backend.models.collab import CollabDraft, DraftSegment, RingState, DraftStatus
from backend.features.analytics.service import (
    compute_draft_analytics,
    compute_user_analytics,
    get_leaderboard,
    record_draft_view,
    record_draft_share,
    clear_store,
)


# Existing tests
@pytest.mark.asyncio
async def test_ring_daily():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            "/api/analytics/ring/daily",
            params={"userId": "test-user"},
        )
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_ring_weekly():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            "/api/analytics/ring/weekly",
            params={"userId": "test-user"},
        )
        assert res.status_code == 200


# Phase 3.4 Analytics Tests


class TestDraftAnalyticsDeterminism:
    """Test that draft analytics are deterministic."""

    def setup_method(self):
        """Clear analytics store before each test."""
        clear_store()

    def test_same_draft_same_time_produces_identical_analytics(self):
        """Same draft + same now => identical analytics."""
        draft = CollabDraft(
            draft_id="draft-1",
            creator_id="user-1",
            title="Test Draft",
            platform="x",
            status=DraftStatus.ACTIVE,
            segments=[
                DraftSegment(
                    segment_id="seg-1",
                    draft_id="draft-1",
                    user_id="user-1",
                    content="First segment",
                    created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
                    segment_order=0,
                )
            ],
            ring_state=RingState(
                draft_id="draft-1",
                current_holder_id="user-1",
                holders_history=["user-1"],
                passed_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            ),
            created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
        )

        fixed_time = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)

        analytics1 = compute_draft_analytics(draft, fixed_time)
        analytics2 = compute_draft_analytics(draft, fixed_time)

        assert analytics1 == analytics2

    def test_different_time_produces_same_metrics(self):
        """Different now => different computed_at, but same metrics."""
        draft = CollabDraft(
            draft_id="draft-1",
            creator_id="user-1",
            title="Test Draft",
            platform="x",
            status=DraftStatus.ACTIVE,
            segments=[],
            ring_state=RingState(
                draft_id="draft-1",
                current_holder_id="user-1",
                holders_history=[],
                passed_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            ),
            created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
        )

        time1 = datetime(2025, 12, 21, 15, 0, 0, tzinfo=timezone.utc)
        time2 = datetime(2025, 12, 21, 16, 0, 0, tzinfo=timezone.utc)

        analytics1 = compute_draft_analytics(draft, time1)
        analytics2 = compute_draft_analytics(draft, time2)

        # Same metrics
        assert analytics1.views == analytics2.views
        assert analytics1.segments_count == analytics2.segments_count
        # Different computed_at
        assert analytics1.computed_at != analytics2.computed_at


class TestDraftAnalyticsBounds:
    """Test that draft analytics stay within sensible bounds."""

    def setup_method(self):
        clear_store()

    def test_views_and_shares_are_non_negative(self):
        """Views and shares must be >= 0."""
        draft = CollabDraft(
            draft_id="draft-1",
            creator_id="user-1",
            title="Test",
            platform="x",
            status=DraftStatus.ACTIVE,
            segments=[],
            ring_state=RingState(
                draft_id="draft-1",
                current_holder_id="user-1",
                holders_history=[],
                passed_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            ),
            created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
        )

        analytics = compute_draft_analytics(draft)
        assert analytics.views >= 0
        assert analytics.shares >= 0

    def test_contributors_count_at_least_one(self):
        """Contributors must be >= 1 (creator is always a contributor)."""
        draft = CollabDraft(
            draft_id="draft-1",
            creator_id="user-1",
            title="Test",
            platform="x",
            status=DraftStatus.ACTIVE,
            segments=[],
            ring_state=RingState(
                draft_id="draft-1",
                current_holder_id="user-1",
                holders_history=[],
                passed_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            ),
            created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
        )

        analytics = compute_draft_analytics(draft)
        assert analytics.contributors_count >= 1


class TestUserAnalyticsDeterminism:
    """Test that user analytics are deterministic."""

    def setup_method(self):
        clear_store()

    def test_same_user_same_drafts_same_time_produces_identical_analytics(self):
        """Same user + same drafts + same now => identical analytics."""
        draft = CollabDraft(
            draft_id="draft-1",
            creator_id="user-1",
            title="Test",
            platform="x",
            status=DraftStatus.ACTIVE,
            segments=[
                DraftSegment(
                    segment_id="seg-1",
                    draft_id="draft-1",
                    user_id="user-1",
                    content="Test segment",
                    created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
                    segment_order=0,
                )
            ],
            ring_state=RingState(
                draft_id="draft-1",
                current_holder_id="user-1",
                holders_history=["user-1"],
                passed_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            ),
            created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
        )

        fixed_time = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)

        analytics1 = compute_user_analytics("user-1", [draft], fixed_time)
        analytics2 = compute_user_analytics("user-1", [draft], fixed_time)

        assert analytics1 == analytics2

    def test_user_with_no_drafts(self):
        """User with no drafts should have all zeros."""
        fixed_time = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)
        analytics = compute_user_analytics("user-unknown", [], fixed_time)

        assert analytics.drafts_created == 0
        assert analytics.drafts_contributed == 0
        assert analytics.segments_written == 0
        assert analytics.rings_held_count == 0


class TestLeaderboardDeterminism:
    """Test that leaderboards are deterministic."""

    def setup_method(self):
        clear_store()

    def test_leaderboard_entries_max_10(self):
        """Leaderboard entries must be at most 10."""
        # Create 15 drafts
        drafts = []
        for i in range(15):
            draft = CollabDraft(
                draft_id=f"draft-{i}",
                creator_id=f"user-{i}",
                title=f"Draft {i}",
                platform="x",
                status=DraftStatus.ACTIVE,
                segments=[
                    DraftSegment(
                        segment_id=f"seg-{i}",
                        draft_id=f"draft-{i}",
                        user_id=f"user-{i}",
                        content=f"Segment {i}",
                        created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
                        segment_order=0,
                    )
                ],
                ring_state=RingState(
                    draft_id=f"draft-{i}",
                    current_holder_id=f"user-{i}",
                    holders_history=[f"user-{i}"],
                    passed_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
                ),
                created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
                updated_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            )
            drafts.append(draft)

        fixed_time = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)
        user_analytics = {f"user-{i}": compute_user_analytics(f"user-{i}", [drafts[i]], fixed_time) for i in range(15)}
        momentum_scores = {f"user-{i}": float(i) for i in range(15)}

        leaderboard = get_leaderboard("collaboration", drafts, user_analytics, momentum_scores, fixed_time)

        assert len(leaderboard.entries) <= 10


class TestLeaderboardSafety:
    """Test that leaderboards never leak secrets."""

    def setup_method(self):
        clear_store()

    def test_leaderboard_entries_have_no_sensitive_fields(self):
        """Leaderboard entries must not contain token_hash, secret, password, etc."""
        draft = CollabDraft(
            draft_id="draft-1",
            creator_id="user-1",
            title="Test",
            platform="x",
            status=DraftStatus.ACTIVE,
            segments=[],
            ring_state=RingState(
                draft_id="draft-1",
                current_holder_id="user-1",
                holders_history=[],
                passed_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            ),
            created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
        )

        fixed_time = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)
        user_analytics = {"user-1": compute_user_analytics("user-1", [draft], fixed_time)}
        momentum_scores = {"user-1": 50.0}

        leaderboard = get_leaderboard("collaboration", [draft], user_analytics, momentum_scores, fixed_time)

        response_str = str(leaderboard.model_dump())
        assert "token_hash" not in response_str
        assert "password" not in response_str
        assert "secret" not in response_str


class TestLeaderboardMessages:
    """Test that leaderboard messages are supportive, never comparative."""

    def setup_method(self):
        clear_store()

    def test_leaderboard_message_is_never_comparative(self):
        """Message should be supportive, not 'you're behind' tone."""
        draft = CollabDraft(
            draft_id="draft-1",
            creator_id="user-1",
            title="Test",
            platform="x",
            status=DraftStatus.ACTIVE,
            segments=[],
            ring_state=RingState(
                draft_id="draft-1",
                current_holder_id="user-1",
                holders_history=[],
                passed_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            ),
            created_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
            updated_at=datetime(2025, 12, 21, 10, 0, 0, tzinfo=timezone.utc),
        )

        fixed_time = datetime(2025, 12, 21, 15, 30, 0, tzinfo=timezone.utc)
        user_analytics = {"user-1": compute_user_analytics("user-1", [draft], fixed_time)}
        momentum_scores = {"user-1": 50.0}

        for metric in ["collaboration", "momentum", "consistency"]:
            leaderboard = get_leaderboard(metric, [draft], user_analytics, momentum_scores, fixed_time)
            # Message should NOT contain: "you're behind", "catch up", "falling behind", etc.
            assert "you're behind" not in leaderboard.message.lower()
            assert "catch up" not in leaderboard.message.lower()
            assert "falling" not in leaderboard.message.lower()

@pytest.mark.asyncio
async def test_ring_daily_empty(monkeypatch):
    import backend.api.analytics as analytics

    def no_posts(user_id: str, start, end):
        return []

    monkeypatch.setattr(analytics, "_mock_fetch_user_posts", no_posts)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.get(
            "/api/analytics/ring/daily",
            params={"userId": "test-user"},
        )
        assert res.status_code == 200
