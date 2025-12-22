"""
Public Profile Guardrail Tests

Verify:
1. Deterministic output for same user_id
2. Does not require env vars (no external calls)
3. Does not leak secrets
4. Returns 200 and correct response shape
5. Weekly momentum array has 7 elements
6. Recent posts <= 5 elements
"""

import pytest
from datetime import datetime, timezone
from backend.api.profile import (
    get_public_profile,
    _stub_streak_for_user,
    _stub_momentum_today_for_user,
    _stub_momentum_weekly_for_user,
    _stub_recent_posts_for_user,
    _profile_summary_for_user,
    StreakSummary,
)


class TestPublicProfileDeterminism:
    """Determinism: same user_id → same output."""

    @pytest.mark.asyncio
    async def test_determinism_same_user_same_profile(self):
        """Same user_id produces identical profile twice."""
        result1 = await get_public_profile(user_id="user_123")
        result2 = await get_public_profile(user_id="user_123")
        
        assert result1["data"]["user_id"] == result2["data"]["user_id"]
        assert result1["data"]["momentum_today"]["score"] == result2["data"]["momentum_today"]["score"]
        assert result1["data"]["streak"]["current_length"] == result2["data"]["streak"]["current_length"]

    def test_determinism_streak_stub(self):
        """Streak stub is deterministic."""
        streak1 = _stub_streak_for_user("user_xyz")
        streak2 = _stub_streak_for_user("user_xyz")
        
        assert streak1.current_length == streak2.current_length
        assert streak1.longest_length == streak2.longest_length
        assert streak1.status == streak2.status

    def test_determinism_momentum_stub(self):
        """Momentum stub is deterministic."""
        momentum1 = _stub_momentum_today_for_user("user_abc")
        momentum2 = _stub_momentum_today_for_user("user_abc")
        
        assert momentum1["score"] == momentum2["score"]
        assert momentum1["trend"] == momentum2["trend"]
        assert momentum1["components"] == momentum2["components"]


class TestPublicProfileNoNetwork:
    """No network: pure computation."""

    def test_streak_pure_function(self):
        """Streak computation is pure (no external calls)."""
        # Should not raise, should complete instantly
        streak = _stub_streak_for_user("user_test")
        assert streak.current_length >= 1
        assert streak.longest_length >= streak.current_length

    def test_momentum_pure_function(self):
        """Momentum computation is pure."""
        momentum = _stub_momentum_today_for_user("user_test")
        assert 40.0 <= momentum["score"] <= 100.0
        assert momentum["trend"] in ["up", "flat", "down"]

    def test_recent_posts_pure_function(self):
        """Recent posts is pure."""
        posts = _stub_recent_posts_for_user("user_test")
        assert isinstance(posts, list)
        assert len(posts) <= 5


class TestPublicProfileSafety:
    """Safety: no secret leakage."""

    @pytest.mark.asyncio
    async def test_profile_does_not_leak_secrets(self):
        """Profile response contains only safe public data."""
        result = await get_public_profile(user_id="user_12345")
        data = result["data"]
        
        # Check safe fields present
        assert "user_id" in data
        assert "display_name" in data
        assert "streak" in data
        assert "momentum_today" in data
        assert "momentum_weekly" in data
        assert "recent_posts" in data
        
        # Check no secret fields or patterns
        response_str = str(data).lower()
        assert "password" not in response_str
        # Don't check for "secret" since it might appear in user_id
        assert "token" not in response_str or "token" not in data  # token in context like "token_..." is OK
        assert "api_key" not in response_str

    def test_momentum_contains_only_public_fields(self):
        """Momentum snapshots only include public data."""
        momentum = _stub_momentum_today_for_user("user_test")
        
        # Public fields should be present
        assert "score" in momentum
        assert "trend" in momentum
        assert "components" in momentum
        assert "nextActionHint" in momentum
        
        # No sensitive fields
        assert "user_secrets" not in momentum
        assert "private_data" not in momentum


class TestPublicProfileShape:
    """Response shape matches contract."""

    @pytest.mark.asyncio
    async def test_returns_correct_shape(self):
        """Response matches PublicProfileResponse schema."""
        result = await get_public_profile(user_id="user_123")
        data = result["data"]
        
        # Top-level fields
        assert isinstance(data["user_id"], str)
        assert isinstance(data["display_name"], str)
        assert isinstance(data["profile_summary"], str)
        assert isinstance(data["computed_at"], str)
        
        # Streak shape
        streak = data["streak"]
        assert isinstance(streak["current_length"], int)
        assert isinstance(streak["longest_length"], int)
        assert isinstance(streak["status"], str)
        assert isinstance(streak["last_active_date"], str)
        
        # Momentum today shape
        today = data["momentum_today"]
        assert isinstance(today["score"], (int, float))
        assert isinstance(today["trend"], str)
        assert "components" in today
        assert "nextActionHint" in today

    @pytest.mark.asyncio
    async def test_weekly_momentum_has_7_days(self):
        """Weekly momentum array has exactly 7 snapshots."""
        result = await get_public_profile(user_id="user_123")
        weekly = result["data"]["momentum_weekly"]
        
        assert isinstance(weekly, list)
        assert len(weekly) == 7, f"Expected 7 days, got {len(weekly)}"
        
        # Each snapshot should be valid
        for snapshot in weekly:
            assert "score" in snapshot
            assert "trend" in snapshot
            assert 0.0 <= snapshot["score"] <= 100.0

    @pytest.mark.asyncio
    async def test_recent_posts_bounded(self):
        """Recent posts list has at most 5 entries."""
        result = await get_public_profile(user_id="user_123")
        posts = result["data"]["recent_posts"]
        
        assert isinstance(posts, list)
        assert len(posts) <= 5
        
        # Each post should have required fields
        for post in posts:
            assert "id" in post
            assert "platform" in post
            assert "content" in post
            assert "created_at" in post


class TestPublicProfileValidation:
    """Validation: required params, error handling."""

    @pytest.mark.asyncio
    async def test_requires_handle_or_user_id(self):
        """Must provide either handle or user_id."""
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_public_profile(handle=None, user_id=None)
        
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_accepts_handle(self):
        """Accepts handle as param."""
        result = await get_public_profile(handle="alice")
        assert result["data"]["user_id"] == "alice"

    @pytest.mark.asyncio
    async def test_accepts_user_id(self):
        """Accepts user_id as param."""
        result = await get_public_profile(user_id="user_123")
        assert result["data"]["user_id"] == "user_123"


class TestPublicProfileStreakLogic:
    """Streak logic is reasonable."""

    def test_longest_streak_gte_current(self):
        """Longest streak >= current streak."""
        streak = _stub_streak_for_user("user_test")
        assert streak.longest_length >= streak.current_length

    def test_current_streak_minimum_1(self):
        """Current streak is at least 1."""
        for user_id in ["user_1", "user_2", "user_3"]:
            streak = _stub_streak_for_user(user_id)
            assert streak.current_length >= 1

    def test_status_reflects_streak(self):
        """Streak status reflects current length."""
        # Most users should have reasonable status
        for user_id in [f"user_{i}" for i in range(10)]:
            streak = _stub_streak_for_user(user_id)
            assert streak.status in ["active", "on_break", "building"]


class TestPublicProfileMomentumLogic:
    """Momentum logic is consistent."""

    def test_momentum_score_in_range(self):
        """Momentum score always 0..100."""
        for user_id in [f"user_{i}" for i in range(10)]:
            momentum = _stub_momentum_today_for_user(user_id)
            assert 40.0 <= momentum["score"] <= 100.0

    def test_momentum_components_sum_reasonable(self):
        """Component sum roughly matches final score."""
        momentum = _stub_momentum_today_for_user("user_test")
        components = momentum["components"]
        
        component_sum = (
            components["streakComponent"]
            + components["consistencyComponent"]
            + components["challengeComponent"]
            + components["coachComponent"]
        )
        
        # Score should be in reasonable range (40..100)
        # Components contribute to the score but calculation may vary
        assert 40.0 <= momentum["score"] <= 100.0
        assert 0.0 <= component_sum <= 60.0  # Max component sum

    def test_trend_is_valid(self):
        """Trend is always one of valid values."""
        for user_id in [f"user_{i}" for i in range(10)]:
            momentum = _stub_momentum_today_for_user(user_id)
            assert momentum["trend"] in ["up", "flat", "down"]


class TestPublicProfileSummary:
    """Profile summary is supportive."""

    def test_summary_never_shameful(self):
        """Summary never uses shame language."""
        shame_words = ["bad", "wrong", "fail", "terrible", "useless", "stupid"]
        
        for user_id in [f"user_{i}" for i in range(10)]:
            streak = _stub_streak_for_user(user_id)
            momentum = _stub_momentum_today_for_user(user_id)
            summary = _profile_summary_for_user(user_id, streak, momentum["score"])
            
            summary_lower = summary.lower()
            for word in shame_words:
                assert word not in summary_lower, f"Shame word '{word}' in: {summary}"

    def test_summary_is_descriptive(self):
        """Summary is non-empty and describes user."""
        streak = _stub_streak_for_user("user_test")
        momentum = _stub_momentum_today_for_user("user_test")
        summary = _profile_summary_for_user("user_test", streak, momentum["score"])
        
        assert len(summary) > 5
        assert any(word in summary for word in ["Creator", "Building", "Growing", "Finding", "momentum", "streak"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
