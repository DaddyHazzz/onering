"""
Phase 8.7: Insight Engine - Computation Service

Derives insights, recommendations, and alerts from Phase 8.6 analytics.
All logic is deterministic and explainable.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from backend.features.insights.models import (
    DraftInsight,
    DraftRecommendation,
    DraftAlert,
    DraftInsightsResponse,
    InsightType,
    InsightSeverity,
    RecommendationAction,
    AlertType,
)
from backend.features.analytics.service import AnalyticsService
from backend.features.analytics.models import DraftAnalyticsSummary, DraftAnalyticsContributors
from backend.features.collaboration.service import get_draft


class InsightEngine:
    """
    Computes actionable insights from draft analytics.
    
    All methods are pure functions (deterministic, no side effects).
    """
    
    # Configuration thresholds (can be made configurable later)
    STALLED_HOURS = 48
    ALERT_NO_ACTIVITY_HOURS = 72
    ALERT_LONG_HOLD_HOURS = 24
    DOMINANT_USER_THRESHOLD = 0.6  # 60% of segments
    
    def __init__(self, analytics_service: AnalyticsService):
        self.analytics_service = analytics_service
    
    def compute_draft_insights(
        self,
        draft_id: str,
        now: Optional[datetime] = None
    ) -> DraftInsightsResponse:
        """
        Compute all insights, recommendations, and alerts for a draft.
        
        Args:
            draft_id: Draft to analyze
            now: Current time (for testing; defaults to utcnow)
        
        Returns:
            Complete insights response
        """
        if now is None:
            now = datetime.now(timezone.utc)
        
        # Fetch draft
        draft = get_draft(draft_id, compute_metrics_flag=False, now=now)
        if not draft:
            raise ValueError(f"Draft {draft_id} not found")
        
        # Fetch analytics
        summary = self.analytics_service.compute_draft_summary(draft)
        contributors = self.analytics_service.compute_contributors(draft)
        
        # Derive insights
        insights = self._derive_insights(summary, contributors, now)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(summary, contributors, insights)
        
        # Compute alerts
        alerts = self._compute_alerts(draft, summary, now)
        
        return DraftInsightsResponse(
            draft_id=draft_id,
            insights=insights,
            recommendations=recommendations,
            alerts=alerts,
            computed_at=now
        )
    
    def _derive_insights(
        self,
        summary: DraftAnalyticsSummary,
        contributors: DraftAnalyticsContributors,
        now: datetime
    ) -> list[DraftInsight]:
        """
        Derive insights from analytics.
        
        Priority order:
        1. Stalled (most critical)
        2. Dominant user (needs attention)
        3. Low engagement (warning)
        4. Healthy (all good)
        """
        insights = []
        
        # Check for stalled draft
        if self._is_stalled(summary, now):
            insights.append(self._create_stalled_insight(summary, now))
            return insights  # Stalled is most critical, return early
        
        # Check for dominant user
        dominant_insight = self._check_dominant_user(contributors)
        if dominant_insight:
            insights.append(dominant_insight)
        
        # Check for low engagement
        if self._is_low_engagement(summary, contributors):
            insights.append(self._create_low_engagement_insight(summary, contributors))
        
        # If no issues, draft is healthy
        if not insights:
            insights.append(self._create_healthy_insight(summary, contributors))
        
        return insights
    
    def _is_stalled(self, summary: DraftAnalyticsSummary, now: datetime) -> bool:
        """Check if draft is stalled (no activity in STALLED_HOURS)."""
        if not summary.last_activity_ts:
            return True  # No activity ever
        
        last_activity = summary.last_activity_ts
        hours_since = (now - last_activity).total_seconds() / 3600
        return hours_since >= self.STALLED_HOURS
    
    def _create_stalled_insight(
        self,
        summary: DraftAnalyticsSummary,
        now: datetime
    ) -> DraftInsight:
        """Create stalled insight."""
        if summary.last_activity_ts:
            last_activity = summary.last_activity_ts
            hours_since = int((now - last_activity).total_seconds() / 3600)
        else:
            hours_since = 0
        
        return DraftInsight(
            type=InsightType.STALLED,
            severity=InsightSeverity.CRITICAL,
            title="Draft is stalled",
            message=f"No activity in {hours_since} hours. Consider passing the ring or inviting collaborators.",
            reason=f"Last activity was {hours_since}h ago (threshold: {self.STALLED_HOURS}h)",
            metrics_snapshot={
                "hours_since_activity": hours_since,
                "threshold_hours": self.STALLED_HOURS,
                "total_segments": summary.total_segments
            }
        )
    
    def _check_dominant_user(
        self,
        contributors: DraftAnalyticsContributors
    ) -> Optional[DraftInsight]:
        """Check if one user dominates contributions."""
        if contributors.total_contributors < 2:
            return None
        
        # Find user with most segments
        max_contributor = max(
            contributors.contributors,
            key=lambda c: c.segments_added_count
        )
        
        total_segments = sum(c.segments_added_count for c in contributors.contributors)
        if total_segments == 0:
            return None
        
        dominance_ratio = max_contributor.segments_added_count / total_segments
        
        if dominance_ratio >= self.DOMINANT_USER_THRESHOLD:
            return DraftInsight(
                type=InsightType.DOMINANT_USER,
                severity=InsightSeverity.WARNING,
                title="One collaborator dominates",
                message=f"User {max_contributor.user_id} contributed {int(dominance_ratio * 100)}% of segments. Consider rotating the ring.",
                reason=f"{max_contributor.user_id} has {max_contributor.segments_added_count}/{total_segments} segments ({dominance_ratio:.1%} > {self.DOMINANT_USER_THRESHOLD:.0%} threshold)",
                metrics_snapshot={
                    "dominant_user_id": max_contributor.user_id,
                    "dominant_user_segments": max_contributor.segments_added_count,
                    "total_segments": total_segments,
                    "dominance_ratio": dominance_ratio
                }
            )
        
        return None
    
    def _is_low_engagement(
        self,
        summary: DraftAnalyticsSummary,
        contributors: DraftAnalyticsContributors
    ) -> bool:
        """Check if engagement is low (only 1 contributor)."""
        return contributors.total_contributors == 1 and summary.total_segments > 0
    
    def _create_low_engagement_insight(
        self,
        summary: DraftAnalyticsSummary,
        contributors: DraftAnalyticsContributors
    ) -> DraftInsight:
        """Create low engagement insight."""
        return DraftInsight(
            type=InsightType.LOW_ENGAGEMENT,
            severity=InsightSeverity.WARNING,
            title="Low collaboration",
            message="Only one person has contributed. Invite collaborators to unlock group creativity.",
            reason=f"Only {contributors.total_contributors} contributor with {summary.total_segments} segments",
            metrics_snapshot={
                "total_contributors": contributors.total_contributors,
                "total_segments": summary.total_segments
            }
        )
    
    def _create_healthy_insight(
        self,
        summary: DraftAnalyticsSummary,
        contributors: DraftAnalyticsContributors
    ) -> DraftInsight:
        """Create healthy insight."""
        return DraftInsight(
            type=InsightType.HEALTHY,
            severity=InsightSeverity.INFO,
            title="Healthy collaboration",
            message=f"{contributors.total_contributors} contributors with {summary.total_segments} segments and {summary.ring_pass_count} ring passes. Keep it up!",
            reason=f"Multiple contributors ({contributors.total_contributors}), active segments ({summary.total_segments}), ring rotation ({summary.ring_pass_count} passes)",
            metrics_snapshot={
                "total_contributors": contributors.total_contributors,
                "total_segments": summary.total_segments,
                "ring_pass_count": summary.ring_pass_count
            }
        )
    
    def _generate_recommendations(
        self,
        summary: DraftAnalyticsSummary,
        contributors: DraftAnalyticsContributors,
        insights: list[DraftInsight]
    ) -> list[DraftRecommendation]:
        """
        Generate actionable recommendations based on insights.
        
        Returns empty list if draft is healthy.
        """
        recommendations = []
        
        # Check insight types
        insight_types = {i.type for i in insights}
        
        if InsightType.STALLED in insight_types:
            # Recommend smart ring pass to most inactive
            most_inactive = self._find_most_inactive_user(contributors)
            if most_inactive:
                recommendations.append(
                    DraftRecommendation(
                        action=RecommendationAction.PASS_RING,
                        target_user_id=most_inactive,
                        reason=f"Ring hasn't moved in {self.STALLED_HOURS}+ hours. Passing to {most_inactive} (least recent contributor) may restart momentum.",
                        confidence=0.85
                    )
                )
        
        if InsightType.DOMINANT_USER in insight_types:
            # Recommend passing ring away from dominant user
            dominant_user_id = None
            for insight in insights:
                if insight.type == InsightType.DOMINANT_USER:
                    dominant_user_id = insight.metrics_snapshot.get("dominant_user_id")
                    break
            
            if dominant_user_id:
                # Find non-dominant user
                non_dominant_users = [
                    c.user_id for c in contributors.contributors
                    if c.user_id != dominant_user_id
                ]
                if non_dominant_users:
                    target = min(non_dominant_users)  # Deterministic: alphabetically first
                    recommendations.append(
                        DraftRecommendation(
                            action=RecommendationAction.PASS_RING,
                            target_user_id=target,
                            reason=f"User {dominant_user_id} has contributed most segments. Passing ring to {target} can encourage balance.",
                            confidence=0.75
                        )
                    )
        
        if InsightType.LOW_ENGAGEMENT in insight_types:
            # Recommend inviting collaborator
            recommendations.append(
                DraftRecommendation(
                    action=RecommendationAction.INVITE_USER,
                    target_user_id=None,
                    reason="Only one contributor so far. Inviting collaborators unlocks group creativity and faster iteration.",
                    confidence=0.9
                )
            )
        
        # If healthy, explicitly return empty list
        return recommendations
    
    def _find_most_inactive_user(
        self,
        contributors: DraftAnalyticsContributors
    ) -> Optional[str]:
        """Find user with fewest segments (or least recent if tie)."""
        if not contributors.contributors:
            return None
        
        # Sort by segments ASC, then by user_id (deterministic)
        sorted_contributors = sorted(
            contributors.contributors,
            key=lambda c: (c.segments_added_count, c.user_id)
        )
        
        return sorted_contributors[0].user_id
    
    def _current_holder_hold_seconds(self, draft, now: datetime) -> float:
        """
        Compute how long the current ring holder has been holding the ring.
        
        Uses ring_state.passed_at as the start time (set at draft creation or last pass).
        Works correctly even with zero ring passes.
        
        Args:
            draft: CollabDraft with ring_state
            now: Current time for deterministic computation
        
        Returns:
            Hold duration in seconds (always >= 0)
        """
        if not draft.ring_state or not draft.ring_state.passed_at:
            # Fallback to draft creation if ring state is missing
            start_ts = draft.created_at
        else:
            # Use ring_state.passed_at (updated on every pass, initialized at creation)
            start_ts = draft.ring_state.passed_at
        
        hold_seconds = (now - start_ts).total_seconds()
        return max(0, hold_seconds)
    
    def _compute_alerts(
        self,
        draft,
        summary: DraftAnalyticsSummary,
        now: datetime
    ) -> list[DraftAlert]:
        """
        Compute threshold-based alerts.
        
        Alerts are stricter than insights (longer thresholds).
        """
        alerts = []
        
        # Alert: No activity in ALERT_NO_ACTIVITY_HOURS
        if summary.last_activity_ts:
            last_activity = summary.last_activity_ts
            hours_since = (now - last_activity).total_seconds() / 3600
            
            if hours_since >= self.ALERT_NO_ACTIVITY_HOURS:
                alerts.append(
                    DraftAlert(
                        alert_type=AlertType.NO_ACTIVITY,
                        triggered_at=now,
                        threshold=f"No activity in {self.ALERT_NO_ACTIVITY_HOURS}+ hours",
                        current_value=int(hours_since),
                        reason=f"Last activity was {int(hours_since)}h ago (alert threshold: {self.ALERT_NO_ACTIVITY_HOURS}h)"
                    )
                )
        
        # Alert: Long ring hold (current holder holding > threshold)
        current_hold_seconds = self._current_holder_hold_seconds(draft, now)
        current_hold_hours = current_hold_seconds / 3600
        if current_hold_hours >= self.ALERT_LONG_HOLD_HOURS:
            alerts.append(
                DraftAlert(
                    alert_type=AlertType.LONG_RING_HOLD,
                    triggered_at=now,
                    threshold=f"Ring held > {self.ALERT_LONG_HOLD_HOURS}h",
                    current_value=round(current_hold_hours, 2),
                    reason=f"Current holder has held the ring for {current_hold_hours:.1f}h (alert threshold: {self.ALERT_LONG_HOLD_HOURS}h). Consider passing the ring."
                )
            )
        
        # Alert: Single contributor (if only 1 contributor and >5 segments)
        if summary.unique_contributors == 1 and summary.total_segments >= 5:
            alerts.append(
                DraftAlert(
                    alert_type=AlertType.SINGLE_CONTRIBUTOR,
                    triggered_at=now,
                    threshold="Only 1 contributor with 5+ segments",
                    current_value=summary.unique_contributors,
                    reason=f"Draft has {summary.total_segments} segments but only {summary.unique_contributors} contributor. Consider inviting collaborators."
                )
            )
        
        return alerts
