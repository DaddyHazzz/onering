"""
Momentum Scoring Engine

Pure, deterministic computation of momentum from available signals.
No external calls, no randomness, no side effects.

Scoring philosophy:
- Base starts at 50 (neutral)
- Streak health contributes 0..25
- Challenge completion contributes 0..15
- Consistency contributes 0..10
- Coach contributes 0..10 (optional)
- Final score clamped to 0..100

Single event cannot swing score >15 points.
Missing data treated optimistically (not as 0).
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from backend.models.momentum import (
    MomentumSnapshot,
    MomentumComponents,
    MomentumTrend,
)


class MomentumScoringEngine:
    """Pure deterministic momentum scoring."""

    # Scoring weights
    BASE_SCORE = 50.0
    STREAK_MAX = 25.0
    CHALLENGE_MAX = 15.0
    CONSISTENCY_MAX = 10.0
    COACH_MAX = 10.0
    MAX_SINGLE_EVENT_DELTA = 15.0

    # Consistency thresholds
    MIN_DAYS_FOR_CONSISTENCY = 3  # Need at least 3 days to assess consistency

    @staticmethod
    def compute_momentum(
        user_id: str,
        date: str,  # YYYY-MM-DD in UTC
        streak_length: int = 0,
        max_possible_streak: int = 30,
        challenge_completed_today: bool = False,
        posts_this_week: int = 0,
        max_posts_per_week: int = 7,
        coach_signals_this_week: int = 0,
        previous_scores: Optional[List[float]] = None,
    ) -> MomentumSnapshot:
        """
        Compute momentum snapshot from available signals.

        Args:
            user_id: User ID
            date: ISO date string (YYYY-MM-DD) in UTC
            streak_length: Current streak (days)
            max_possible_streak: Benchmark streak length (default 30)
            challenge_completed_today: Was today's challenge completed?
            posts_this_week: Number of posts in last 7 days
            max_posts_per_week: Target posts per week (for consistency calc)
            coach_signals_this_week: Number of times coach feedback was requested this week
            previous_scores: List of momentum scores for last 7 days (for trend calc)

        Returns:
            MomentumSnapshot with score, components, trend, and action hint
        """
        # Score each component
        streak_component = MomentumScoringEngine._score_streak(streak_length, max_possible_streak)
        challenge_component = MomentumScoringEngine._score_challenge(challenge_completed_today)
        consistency_component = MomentumScoringEngine._score_consistency(
            posts_this_week, max_posts_per_week
        )
        coach_component = MomentumScoringEngine._score_coach(coach_signals_this_week)

        components = MomentumComponents(
            streak_component=streak_component,
            challenge_component=challenge_component,
            consistency_component=consistency_component,
            coach_component=coach_component,
        )

        # Calculate total score
        raw_score = MomentumScoringEngine.BASE_SCORE + sum([
            streak_component,
            challenge_component,
            consistency_component,
            coach_component,
        ])
        score = max(0.0, min(100.0, raw_score))  # Clamp to 0..100

        # Calculate trend (vs 7-day average)
        trend = MomentumScoringEngine._calculate_trend(score, previous_scores)

        # Generate action hint
        next_action_hint = MomentumScoringEngine._generate_hint(
            score, trend, challenge_completed_today, coach_signals_this_week
        )

        snapshot = MomentumSnapshot(
            user_id=user_id,
            date=date,
            score=score,
            trend=trend,
            components=components,
            next_action_hint=next_action_hint,
            computed_at=datetime.now(timezone.utc),
        )

        snapshot.validate()
        return snapshot

    @staticmethod
    def _score_streak(current_streak: int, max_streak: int = 30) -> float:
        """
        Streak health score, 0..25.

        Longer streaks = higher confidence and momentum.
        Benchmarked against max_streak (e.g., 30 days is excellent).
        """
        if current_streak <= 0:
            return 0.0
        if current_streak >= max_streak:
            return MomentumScoringEngine.STREAK_MAX

        # Linear scale: current / max * 25
        ratio = min(1.0, current_streak / max_streak)
        return ratio * MomentumScoringEngine.STREAK_MAX

    @staticmethod
    def _score_challenge(completed_today: bool) -> float:
        """
        Challenge completion score, 0 or 15.

        Completing today's challenge shows commitment and direction.
        """
        return MomentumScoringEngine.CHALLENGE_MAX if completed_today else 0.0

    @staticmethod
    def _score_consistency(posts_this_week: int, max_posts_per_week: int = 7) -> float:
        """
        Consistency score, 0..10.

        Regular posting (at least a few times per week) shows steady momentum,
        not viral spikes. Rewarded generously.
        """
        if posts_this_week <= 0:
            return 0.0
        if posts_this_week >= max_posts_per_week:
            return MomentumScoringEngine.CONSISTENCY_MAX

        # Partial credit for partial consistency
        ratio = min(1.0, posts_this_week / max_posts_per_week)
        return ratio * MomentumScoringEngine.CONSISTENCY_MAX

    @staticmethod
    def _score_coach(coach_signals_this_week: int) -> float:
        """
        Coach engagement score, 0..10.

        Requesting coach feedback shows intentional improvement.
        Cap at 4+ signals per week (diminishing returns).
        """
        if coach_signals_this_week <= 0:
            return 0.0
        if coach_signals_this_week >= 4:
            return MomentumScoringEngine.COACH_MAX

        # Linear scale: each signal adds 2.5 points
        return min(MomentumScoringEngine.COACH_MAX, coach_signals_this_week * 2.5)

    @staticmethod
    def _calculate_trend(
        current_score: float, previous_scores: Optional[List[float]] = None
    ) -> MomentumTrend:
        """
        Calculate trend by comparing current score to 7-day rolling average.

        Args:
            current_score: Today's momentum score
            previous_scores: List of scores for last 7 days (most recent first)

        Returns:
            "up", "flat", or "down"
        """
        if not previous_scores or len(previous_scores) < 3:
            # Insufficient history: no clear trend
            return "flat"

        avg = sum(previous_scores) / len(previous_scores)

        # Thresholds: only significant deltas count as trend
        if current_score >= avg + 5.0:
            return "up"
        elif current_score <= avg - 5.0:
            return "down"
        else:
            return "flat"

    @staticmethod
    def _generate_hint(
        score: float,
        trend: MomentumTrend,
        challenge_completed_today: bool,
        coach_signals_this_week: int,
    ) -> str:
        """
        Generate supportive, action-inviting hint.

        Never shaming. Always points to next step.
        """
        if score >= 80.0:
            if challenge_completed_today:
                return "You're in flow. Keep riding this wave today."
            else:
                return "Strong week. Complete today's challenge to cap it off."

        if score >= 60.0:
            if coach_signals_this_week == 0:
                return "Solid momentum. Try getting coach feedback on your next draft."
            else:
                return "You're steady. One more push today locks in progress."

        if score >= 40.0:
            if challenge_completed_today:
                return "Good start. Check coach feedback next time for polish."
            else:
                return "Room to grow. Complete today's challenge for momentum."

        # Below 40: emphasize small wins and recovery
        if trend == "down":
            return "Momentum is dipping. Post something small today to rebuild."
        else:
            return "Building back up. A small post today counts."

    @staticmethod
    def validate_snapshot(snapshot: MomentumSnapshot) -> bool:
        """Verify snapshot is valid and stable."""
        snapshot.validate()
        # Could add additional cross-field checks here
        return True
