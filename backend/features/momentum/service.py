"""
Momentum Service

Adapts input from streak, challenge, and posting systems,
then computes momentum snapshot deterministically.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple
from backend.models.momentum import MomentumSnapshot
from backend.features.momentum.scoring_engine import MomentumScoringEngine


class MomentumService:
    """Deterministic momentum computation with graceful fallbacks."""

    @staticmethod
    def compute_today_momentum(
        user_id: str,
        streak_service=None,
        challenge_service=None,
        analytics_service=None,
    ) -> MomentumSnapshot:
        """
        Compute momentum for today.

        Gathers inputs from services if available; treats missing data optimistically.

        Args:
            user_id: User ID
            streak_service: StreakService instance (optional)
            challenge_service: ChallengeService instance (optional)
            analytics_service: AnalyticsService instance (optional)

        Returns:
            MomentumSnapshot for today
        """
        today_utc = datetime.now(timezone.utc).date()
        today_str = today_utc.isoformat()

        # Gather inputs with safe fallbacks
        streak_length = MomentumService._get_streak_length(user_id, streak_service)
        challenge_completed = MomentumService._get_challenge_completion(user_id, challenge_service)
        posts_this_week = MomentumService._get_posts_this_week(user_id, analytics_service)
        coach_signals = MomentumService._get_coach_signals_this_week(user_id, analytics_service)
        previous_scores = MomentumService._get_previous_scores(user_id, analytics_service)

        # Compute
        snapshot = MomentumScoringEngine.compute_momentum(
            user_id=user_id,
            date=today_str,
            streak_length=streak_length,
            challenge_completed_today=challenge_completed,
            posts_this_week=posts_this_week,
            coach_signals_this_week=coach_signals,
            previous_scores=previous_scores,
        )

        return snapshot

    @staticmethod
    def compute_weekly_momentum(
        user_id: str,
        streak_service=None,
        challenge_service=None,
        analytics_service=None,
    ) -> List[MomentumSnapshot]:
        """
        Compute momentum for last 7 days (most recent first).

        Args:
            user_id: User ID
            streak_service: StreakService instance (optional)
            challenge_service: ChallengeService instance (optional)
            analytics_service: AnalyticsService instance (optional)

        Returns:
            List of MomentumSnapshot objects for last 7 days, most recent first
        """
        today_utc = datetime.now(timezone.utc).date()
        snapshots = []

        for days_back in range(7):
            date_utc = today_utc - timedelta(days=days_back)
            date_str = date_utc.isoformat()

            # For historical days, we'd normally read from stored snapshots.
            # For now, recompute using "as-if" data (simplified).
            # In production, read MomentumSnapshot from store.
            streak_length = MomentumService._get_streak_length_on_date(
                user_id, date_utc, streak_service
            )
            challenge_completed = MomentumService._get_challenge_completion_on_date(
                user_id, date_utc, challenge_service
            )
            posts_up_to_week = MomentumService._get_posts_for_week_ending(
                user_id, date_utc, analytics_service
            )
            coach_signals_up_to_week = MomentumService._get_coach_signals_for_week_ending(
                user_id, date_utc, analytics_service
            )

            # For historical trend, use data up to that point
            previous_scores = MomentumService._get_previous_scores_before(
                user_id, date_utc, analytics_service
            )

            snapshot = MomentumScoringEngine.compute_momentum(
                user_id=user_id,
                date=date_str,
                streak_length=streak_length,
                challenge_completed_today=challenge_completed,
                posts_this_week=posts_up_to_week,
                coach_signals_this_week=coach_signals_up_to_week,
                previous_scores=previous_scores,
            )
            snapshots.append(snapshot)

        return snapshots

    # ============ Input Adapters ============

    @staticmethod
    def _get_streak_length(user_id: str, service=None) -> int:
        """Get current streak length, default 0."""
        if not service:
            return 0
        try:
            streak = service.get_current_streak(user_id)
            return streak.length if streak else 0
        except Exception:
            return 0

    @staticmethod
    def _get_streak_length_on_date(user_id: str, date, service=None) -> int:
        """Get streak length as of a past date, default 0."""
        if not service:
            return 0
        try:
            streak = service.get_streak_on_date(user_id, date)
            return streak.length if streak else 0
        except Exception:
            return 0

    @staticmethod
    def _get_challenge_completion(user_id: str, service=None) -> bool:
        """Check if today's challenge was completed."""
        if not service:
            return False
        try:
            today_utc = datetime.now(timezone.utc).date()
            result = service.get_challenge_for_date(user_id, today_utc)
            return result.completed if result else False
        except Exception:
            return False

    @staticmethod
    def _get_challenge_completion_on_date(user_id: str, date, service=None) -> bool:
        """Check if challenge was completed on a past date."""
        if not service:
            return False
        try:
            result = service.get_challenge_for_date(user_id, date)
            return result.completed if result else False
        except Exception:
            return False

    @staticmethod
    def _get_posts_this_week(user_id: str, service=None) -> int:
        """Get number of posts in last 7 days, default 0."""
        if not service:
            return 0
        try:
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=7)
            posts = service.get_posts_in_range(user_id, start_date, end_date)
            return len(posts) if posts else 0
        except Exception:
            return 0

    @staticmethod
    def _get_posts_for_week_ending(user_id: str, date, service=None) -> int:
        """Get posts in 7 days ending on date."""
        if not service:
            return 0
        try:
            end_date = date
            start_date = date - timedelta(days=6)
            posts = service.get_posts_in_range(user_id, start_date, end_date)
            return len(posts) if posts else 0
        except Exception:
            return 0

    @staticmethod
    def _get_coach_signals_this_week(user_id: str, service=None) -> int:
        """Get number of coach feedback requests this week."""
        if not service:
            return 0
        try:
            end_date = datetime.now(timezone.utc).date()
            start_date = end_date - timedelta(days=7)
            events = service.get_events_in_range(
                user_id, "coach.feedback_generated", start_date, end_date
            )
            return len(events) if events else 0
        except Exception:
            return 0

    @staticmethod
    def _get_coach_signals_for_week_ending(user_id: str, date, service=None) -> int:
        """Get coach signals in 7 days ending on date."""
        if not service:
            return 0
        try:
            end_date = date
            start_date = date - timedelta(days=6)
            events = service.get_events_in_range(
                user_id, "coach.feedback_generated", start_date, end_date
            )
            return len(events) if events else 0
        except Exception:
            return 0

    @staticmethod
    def _get_previous_scores(user_id: str, service=None) -> Optional[List[float]]:
        """Get previous 7 scores for trend calculation, None if unavailable."""
        if not service:
            return None
        try:
            today = datetime.now(timezone.utc).date()
            scores = []
            for days_back in range(1, 8):
                date = today - timedelta(days=days_back)
                score = service.get_momentum_score_for_date(user_id, date)
                if score is not None:
                    scores.append(score)
            return scores if scores else None
        except Exception:
            return None

    @staticmethod
    def _get_previous_scores_before(
        user_id: str, date, service=None
    ) -> Optional[List[float]]:
        """Get previous 7 scores before date."""
        if not service:
            return None
        try:
            scores = []
            for days_back in range(1, 8):
                check_date = date - timedelta(days=days_back)
                score = service.get_momentum_score_for_date(user_id, check_date)
                if score is not None:
                    scores.append(score)
            return scores if scores else None
        except Exception:
            return None
