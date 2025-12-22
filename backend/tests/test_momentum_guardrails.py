"""
Momentum Guardrail Tests

Verify:
1. Determinism: same inputs => same score
2. Stability: single event cannot swing >15 points
3. Missing data: score not 0, still produces usable hint
4. Component influences: streak/challenge/consistency/coach each impact score
5. Clamping: score always 0..100
6. Trend calculation: accurate trend vs rolling average
7. Next action hints: never shameful, always actionable
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.models.momentum import (
    MomentumSnapshot,
    MomentumComponents,
)
from backend.features.momentum.scoring_engine import MomentumScoringEngine


class TestMomentumDeterminism:
    """Determinism: identical inputs yield identical outputs."""

    def test_determinism_same_inputs_same_score(self):
        """Same inputs must produce identical score."""
        inputs = {
            "user_id": "user_123",
            "date": "2025-12-21",
            "streak_length": 5,
            "challenge_completed_today": True,
            "posts_this_week": 3,
            "coach_signals_this_week": 1,
        }

        snapshot1 = MomentumScoringEngine.compute_momentum(**inputs)
        snapshot2 = MomentumScoringEngine.compute_momentum(**inputs)

        assert snapshot1.score == snapshot2.score
        assert snapshot1.trend == snapshot2.trend
        assert snapshot1.components.streak_component == snapshot2.components.streak_component
        assert snapshot1.components.challenge_component == snapshot2.components.challenge_component

    def test_determinism_components_reproducible(self):
        """Component scores are deterministic."""
        for streak in [0, 5, 15, 30]:
            score1 = MomentumScoringEngine._score_streak(streak, max_streak=30)
            score2 = MomentumScoringEngine._score_streak(streak, max_streak=30)
            assert score1 == score2, f"Streak {streak} not deterministic"

        for completed in [True, False]:
            score1 = MomentumScoringEngine._score_challenge(completed)
            score2 = MomentumScoringEngine._score_challenge(completed)
            assert score1 == score2, f"Challenge {completed} not deterministic"


class TestMomentumStability:
    """Stability: single event should not swing score >15 points."""

    def test_stability_streak_change(self):
        """Adding one day to streak should not swing >15 points."""
        base = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=False,
            posts_this_week=0,
            coach_signals_this_week=0,
        )

        new_streak = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=6,
            challenge_completed_today=False,
            posts_this_week=0,
            coach_signals_this_week=0,
        )

        delta = abs(new_streak.score - base.score)
        assert delta <= 15.0, f"Streak change swung {delta} > 15"

    def test_stability_challenge_completion(self):
        """Completing today's challenge should not swing >15."""
        base = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=False,
            posts_this_week=3,
            coach_signals_this_week=0,
        )

        completed = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=True,
            posts_this_week=3,
            coach_signals_this_week=0,
        )

        delta = abs(completed.score - base.score)
        assert delta <= 15.0, f"Challenge completion swung {delta} > 15"


class TestMomentumMissingData:
    """Missing data: score should never be 0, always usable."""

    def test_missing_data_no_zero_score(self):
        """All zero inputs should not produce score of 0."""
        snapshot = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=0,
            challenge_completed_today=False,
            posts_this_week=0,
            coach_signals_this_week=0,
        )

        # Base score is 50, so minimum should be >= 50
        assert snapshot.score >= 40.0, f"Score too low with zero inputs: {snapshot.score}"

    def test_missing_data_has_action_hint(self):
        """Even with no signals, should have actionable hint."""
        snapshot = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=0,
            challenge_completed_today=False,
            posts_this_week=0,
            coach_signals_this_week=0,
        )

        assert snapshot.next_action_hint
        assert len(snapshot.next_action_hint) > 10
        assert "post" in snapshot.next_action_hint.lower() or "challenge" in snapshot.next_action_hint.lower()


class TestMomentumComponentInfluences:
    """Components: each contributor properly influences score."""

    def test_streak_influence(self):
        """Higher streak => higher streak_component."""
        low_streak = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=1,
            challenge_completed_today=False,
            posts_this_week=0,
            coach_signals_this_week=0,
        )

        high_streak = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=20,
            challenge_completed_today=False,
            posts_this_week=0,
            coach_signals_this_week=0,
        )

        assert high_streak.components.streak_component > low_streak.components.streak_component
        assert high_streak.score > low_streak.score

    def test_challenge_influence(self):
        """Challenge completion => higher score."""
        no_challenge = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=False,
            posts_this_week=2,
            coach_signals_this_week=0,
        )

        with_challenge = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=True,
            posts_this_week=2,
            coach_signals_this_week=0,
        )

        assert with_challenge.components.challenge_component == 15.0
        assert no_challenge.components.challenge_component == 0.0
        assert with_challenge.score > no_challenge.score

    def test_consistency_influence(self):
        """More posts => higher consistency_component."""
        few_posts = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=False,
            posts_this_week=1,
            coach_signals_this_week=0,
        )

        many_posts = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=False,
            posts_this_week=7,
            coach_signals_this_week=0,
        )

        assert many_posts.components.consistency_component >= few_posts.components.consistency_component
        assert many_posts.score >= few_posts.score

    def test_coach_influence(self):
        """Coach signals => higher coach_component."""
        no_coach = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=False,
            posts_this_week=2,
            coach_signals_this_week=0,
        )

        with_coach = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=False,
            posts_this_week=2,
            coach_signals_this_week=2,
        )

        assert with_coach.components.coach_component > no_coach.components.coach_component
        assert with_coach.score > no_coach.score


class TestMomentumClamping:
    """Clamping: score always 0..100."""

    def test_score_never_below_zero(self):
        """Score clamped >= 0."""
        snapshot = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=0,
            challenge_completed_today=False,
            posts_this_week=0,
            coach_signals_this_week=0,
        )
        assert snapshot.score >= 0.0

    def test_score_never_above_100(self):
        """Score clamped <= 100."""
        snapshot = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=100,
            challenge_completed_today=True,
            posts_this_week=7,
            coach_signals_this_week=4,
        )
        assert snapshot.score <= 100.0

    def test_all_components_in_range(self):
        """Each component within defined range."""
        snapshot = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=15,
            challenge_completed_today=True,
            posts_this_week=5,
            coach_signals_this_week=2,
        )

        assert 0.0 <= snapshot.components.streak_component <= 25.0
        assert 0.0 <= snapshot.components.challenge_component <= 15.0
        assert 0.0 <= snapshot.components.consistency_component <= 10.0
        assert 0.0 <= snapshot.components.coach_component <= 10.0


class TestMomentumTrendCalculation:
    """Trend: calculated accurately vs rolling average."""

    def test_trend_up_higher_than_average(self):
        """Current score > avg => up trend."""
        previous = [40.0, 45.0, 50.0]
        trend = MomentumScoringEngine._calculate_trend(60.0, previous)
        assert trend == "up"

    def test_trend_down_lower_than_average(self):
        """Current score < avg => down trend."""
        previous = [60.0, 65.0, 70.0]
        trend = MomentumScoringEngine._calculate_trend(50.0, previous)
        assert trend == "down"

    def test_trend_flat_near_average(self):
        """Current score ~= avg => flat trend."""
        previous = [50.0, 52.0, 51.0]
        trend = MomentumScoringEngine._calculate_trend(51.0, previous)
        assert trend == "flat"

    def test_trend_insufficient_history(self):
        """Few previous scores => flat trend."""
        trend = MomentumScoringEngine._calculate_trend(70.0, [50.0])
        assert trend == "flat"


class TestMomentumActionHints:
    """Action hints: never shameful, always actionable."""

    def test_hint_never_empty(self):
        """Hint always present."""
        for streak in [0, 5, 20]:
            for challenge in [True, False]:
                for coach in [0, 1, 3]:
                    snapshot = MomentumScoringEngine.compute_momentum(
                        user_id="user_123",
                        date="2025-12-21",
                        streak_length=streak,
                        challenge_completed_today=challenge,
                        posts_this_week=2,
                        coach_signals_this_week=coach,
                    )
                    assert snapshot.next_action_hint
                    assert len(snapshot.next_action_hint) > 0

    def test_hint_never_shameful(self):
        """Hint never uses shame language."""
        shame_words = ["bad", "wrong", "fail", "terrible", "useless", "stupid"]

        for streak in [0, 5]:
            for challenge in [True, False]:
                snapshot = MomentumScoringEngine.compute_momentum(
                    user_id="user_123",
                    date="2025-12-21",
                    streak_length=streak,
                    challenge_completed_today=challenge,
                    posts_this_week=1,
                    coach_signals_this_week=0,
                )
                hint_lower = snapshot.next_action_hint.lower()
                for word in shame_words:
                    assert word not in hint_lower, f"Shame word '{word}' in hint: {snapshot.next_action_hint}"

    def test_hint_offers_action(self):
        """Hint always points to next step."""
        snapshot = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=0,
            challenge_completed_today=False,
            posts_this_week=0,
            coach_signals_this_week=0,
        )

        action_keywords = ["post", "challenge", "today", "complete", "try", "coach"]
        hint_lower = snapshot.next_action_hint.lower()
        has_action = any(kw in hint_lower for kw in action_keywords)
        assert has_action, f"No action keyword in hint: {snapshot.next_action_hint}"


class TestMomentumValidation:
    """Validation: snapshots are valid and satisfy contracts."""

    def test_snapshot_validates(self):
        """Snapshot passes validation."""
        snapshot = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=True,
            posts_this_week=3,
            coach_signals_this_week=1,
        )

        # Should not raise
        snapshot.validate()

    def test_snapshot_to_dict(self):
        """Snapshot serializes to dict."""
        snapshot = MomentumScoringEngine.compute_momentum(
            user_id="user_123",
            date="2025-12-21",
            streak_length=5,
            challenge_completed_today=True,
            posts_this_week=3,
            coach_signals_this_week=1,
        )

        d = snapshot.to_dict()
        assert d["userId"] == "user_123"
        assert d["date"] == "2025-12-21"
        assert 0.0 <= d["score"] <= 100.0
        assert d["trend"] in ["up", "flat", "down"]
        assert "streakComponent" in d["components"]
        assert "nextActionHint" in d


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
