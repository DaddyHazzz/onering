"""
backend/features/analytics/service.py
Analytics service for Phase 8.6 — deterministic computation from audit events and segments
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict
from backend.models.collab import CollabDraft, DraftSegment
from backend.features.collaboration.service import get_draft
from backend.core.database import get_db_session, audit_events, draft_segments, drafts
from backend.core.errors import NotFoundError, PermissionError
from sqlalchemy import select, and_, func, text
from backend.features.analytics.models import (
    DraftAnalyticsSummary, ContributorMetrics, DraftAnalyticsContributors,
    RingHold, RingPass, RingRecommendation, DraftAnalyticsRing,
    DailyActivityMetrics, DraftAnalyticsDaily, InactivityRisk
)


class AnalyticsService:
    """Deterministic analytics computation from audit events and segments"""
    
    @staticmethod
    def compute_draft_summary(draft: CollabDraft) -> DraftAnalyticsSummary:
        """Compute summary metrics for a draft"""
        
        # Get all segments for word count
        total_segments = len(draft.segments)
        total_words = sum(len(s.content.split()) for s in draft.segments)
        
        # Get unique contributors from segments + ring history
        contributors = set(s.user_id for s in draft.segments)
        contributors.update(draft.ring_state.holders_history)
        unique_contributors = len(contributors)
        
        # Last activity: max of segment creation and ring pass time
        last_activity_ts = None
        if draft.segments:
            last_activity_ts = max(s.created_at for s in draft.segments)
        if draft.ring_state.last_passed_at:
            if last_activity_ts:
                last_activity_ts = max(last_activity_ts, draft.ring_state.last_passed_at)
            else:
                last_activity_ts = draft.ring_state.last_passed_at
        
        # Ring pass count from holders history (N holders means N-1 passes to get there)
        ring_pass_count = max(0, len(draft.ring_state.holders_history) - 1)
        
        # Compute average hold time from audit events
        avg_hold_seconds = AnalyticsService._compute_avg_hold_seconds(draft)
        
        # Assess inactivity risk
        inactivity_risk = AnalyticsService._assess_inactivity_risk(last_activity_ts, ring_pass_count)
        
        return DraftAnalyticsSummary(
            draft_id=draft.draft_id,
            total_segments=total_segments,
            total_words=total_words,
            unique_contributors=unique_contributors,
            last_activity_ts=last_activity_ts,
            ring_pass_count=ring_pass_count,
            avg_time_holding_ring_seconds=avg_hold_seconds,
            inactivity_risk=inactivity_risk
        )
    
    @staticmethod
    def compute_contributors(draft: CollabDraft) -> DraftAnalyticsContributors:
        """Compute per-contributor metrics"""
        
        # Build contributor metrics from segments and ring history
        contrib_data: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "segments_count": 0,
            "words": 0,
            "first_ts": None,
            "last_ts": None,
            "ring_holds": 0,
            "hold_seconds": 0,
            "suggestions_count": 0,
            "votes_count": 0,
        })
        
        # From segments
        for segment in draft.segments:
            user_id = segment.user_id
            contrib_data[user_id]["segments_count"] += 1
            contrib_data[user_id]["words"] += len(segment.content.split())
            
            if not contrib_data[user_id]["first_ts"] or segment.created_at < contrib_data[user_id]["first_ts"]:
                contrib_data[user_id]["first_ts"] = segment.created_at
            
            if not contrib_data[user_id]["last_ts"] or segment.created_at > contrib_data[user_id]["last_ts"]:
                contrib_data[user_id]["last_ts"] = segment.created_at
        
        # From ring history (compute holds from consecutive pairs)
        holds_by_user = AnalyticsService._compute_holds_from_history(draft)
        for user_id, holds in holds_by_user.items():
            contrib_data[user_id]["ring_holds"] = len(holds)
            contrib_data[user_id]["hold_seconds"] = sum(h.seconds for h in holds)
        
        # From wait mode (if present)
        wait_counts = AnalyticsService._compute_wait_counts(draft.draft_id)
        for user_id, counts in wait_counts.items():
            contrib_data[user_id]["suggestions_count"] = counts.get("suggestions", 0)
            contrib_data[user_id]["votes_count"] = counts.get("votes", 0)
        
        # Build response objects, sorted by last contribution DESC
        contributors = []
        for user_id, data in contrib_data.items():
            contributors.append(ContributorMetrics(
                user_id=user_id,
                segments_added_count=data["segments_count"],
                words_added=data["words"],
                first_contribution_ts=data["first_ts"],
                last_contribution_ts=data["last_ts"],
                ring_holds_count=data["ring_holds"],
                total_hold_seconds=data["hold_seconds"],
                suggestions_queued_count=data["suggestions_count"],
                votes_cast_count=data["votes_count"],
            ))
        
        # Sort by last contribution DESC, then by user_id for stability
        contributors.sort(key=lambda c: (c.last_contribution_ts or datetime(1970, 1, 1, tzinfo=timezone.utc), c.user_id), reverse=True)
        
        return DraftAnalyticsContributors(
            draft_id=draft.draft_id,
            contributors=contributors,
            total_contributors=len(contributors)
        )
    
    @staticmethod
    def compute_ring_dynamics(draft: CollabDraft) -> DraftAnalyticsRing:
        """Compute ring holding and passing dynamics"""
        
        # Get holds from history
        holds_by_user = AnalyticsService._compute_holds_from_history(draft)
        all_holds = []
        for holds in holds_by_user.values():
            all_holds.extend(holds)
        
        # Sort by start_ts DESC (most recent first), take last 10
        all_holds.sort(key=lambda h: h.start_ts, reverse=True)
        holds = all_holds[:10]
        
        # Get passes from history
        passes = AnalyticsService._compute_passes_from_history(draft)
        # Sort by ts DESC (most recent first), take last 10
        passes.sort(key=lambda p: p.ts, reverse=True)
        passes = passes[:10]
        
        # Compute recommendation: most inactive contributor
        recommendation = AnalyticsService._recommend_next_holder(draft)
        
        return DraftAnalyticsRing(
            draft_id=draft.draft_id,
            current_holder_id=draft.ring_state.current_holder_id,
            holds=holds,
            passes=passes,
            recommendation=recommendation
        )
    
    @staticmethod
    def compute_daily_activity(draft: CollabDraft, days: int = 14) -> DraftAnalyticsDaily:
        """Compute daily activity sparkline (last N days)"""
        
        # Build day buckets in UTC
        now = datetime.now(timezone.utc)
        day_metrics: Dict[str, DailyActivityMetrics] = {}
        
        for i in range(days):
            date_obj = (now - timedelta(days=i)).date()
            date_str = date_obj.isoformat()
            day_metrics[date_str] = DailyActivityMetrics(
                date=date_str,
                segments_added=0,
                ring_passes=0
            )
        
        # Count segments per day
        for segment in draft.segments:
            date_str = segment.created_at.astimezone(timezone.utc).date().isoformat()
            if date_str in day_metrics:
                day_metrics[date_str].segments_added += 1
        
        # Count ring passes per day (from holders_history transitions)
        # A pass occurs between consecutive holders
        for i in range(len(draft.ring_state.holders_history) - 1):
            # We don't have exact pass times, so use ring_state.last_passed_at as proxy
            # For determinism, attribute last pass to the day it occurred
            if draft.ring_state.last_passed_at:
                date_str = draft.ring_state.last_passed_at.astimezone(timezone.utc).date().isoformat()
                if date_str in day_metrics:
                    day_metrics[date_str].ring_passes += 1
        
        # Sort by date ASC (chronological)
        result = sorted(day_metrics.values(), key=lambda m: m.date)
        
        return DraftAnalyticsDaily(
            draft_id=draft.draft_id,
            days=result,
            window_days=days
        )
    
    # ---- HELPER METHODS (deterministic computation) ----
    
    @staticmethod
    def _compute_avg_hold_seconds(draft: CollabDraft) -> Optional[float]:
        """Compute average hold duration from ring history"""
        
        holds = []
        for user_id in draft.ring_state.holders_history:
            user_holds = AnalyticsService._compute_holds_from_history(draft).get(user_id, [])
            holds.extend(user_holds)
        
        if not holds:
            return None
        
        total_seconds = sum(h.seconds for h in holds)
        return total_seconds / len(holds)
    
    @staticmethod
    def _assess_inactivity_risk(last_activity_ts: Optional[datetime], ring_pass_count: int) -> InactivityRisk:
        """Determine inactivity risk based on time and activity"""
        
        if not last_activity_ts:
            return InactivityRisk.HIGH  # No activity at all
        
        now = datetime.now(timezone.utc)
        hours_since = (now - last_activity_ts.astimezone(timezone.utc)).total_seconds() / 3600
        
        # Heuristic: if > 48 hours since last activity, risk is HIGH
        # If > 24 hours and few passes, MEDIUM
        # Otherwise LOW
        if hours_since > 48:
            return InactivityRisk.HIGH
        elif hours_since > 24 and ring_pass_count < 2:
            return InactivityRisk.MEDIUM
        else:
            return InactivityRisk.LOW
    
    @staticmethod
    def _compute_holds_from_history(draft: CollabDraft) -> Dict[str, List[RingHold]]:
        """Compute ring holds from holders_history and timestamps"""
        
        holds_by_user: Dict[str, List[RingHold]] = defaultdict(list)
        history = draft.ring_state.holders_history
        
        if not history:
            return holds_by_user
        
        # For each consecutive pair, create a hold record
        for i in range(len(history)):
            current_user = history[i]
            
            # Start time: draft creation for first holder, last_passed_at proxy for others
            if i == 0:
                start_ts = draft.created_at
            else:
                # Use last_passed_at as proxy (not ideal but deterministic)
                start_ts = draft.ring_state.last_passed_at or draft.created_at
            
            # End time: start time of next holder (determined by last_passed_at)
            if i < len(history) - 1:
                # Next holder started when this one passed (use same timestamp for now)
                end_ts = draft.ring_state.last_passed_at
                seconds = int((end_ts - start_ts).total_seconds()) if end_ts else 0
                
                holds_by_user[current_user].append(RingHold(
                    user_id=current_user,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    seconds=max(0, seconds)  # Prevent negative
                ))
            else:
                # Current holder: no end time yet
                now = datetime.now(timezone.utc)
                seconds = int((now - start_ts).total_seconds())
                holds_by_user[current_user].append(RingHold(
                    user_id=current_user,
                    start_ts=start_ts,
                    end_ts=None,
                    seconds=seconds
                ))
        
        return holds_by_user
    
    @staticmethod
    def _compute_passes_from_history(draft: CollabDraft) -> List[RingPass]:
        """Compute ring passes from holders_history"""
        
        passes = []
        history = draft.ring_state.holders_history
        
        if len(history) < 2:
            return passes
        
        # For each transition, create a pass record
        for i in range(len(history) - 1):
            from_user = history[i]
            to_user = history[i + 1]
            ts = draft.ring_state.last_passed_at or draft.created_at  # Proxy timestamp
            
            passes.append(RingPass(
                from_user_id=from_user,
                to_user_id=to_user,
                ts=ts,
                strategy=None  # Would need audit events to get strategy
            ))
        
        return passes
    
    @staticmethod
    def _recommend_next_holder(draft: CollabDraft) -> Optional[RingRecommendation]:
        """Recommend next ring holder based on inactivity heuristic"""
        
        # Get all eligible candidates (collaborators + creator, excluding current holder)
        candidates = [draft.creator_id] + draft.collaborators
        eligible = [u for u in candidates if u != draft.ring_state.current_holder_id]
        
        if not eligible:
            return None
        
        # Heuristic: pick most_inactive contributor (fewest recent segments)
        # Build activity map from segments
        activity: Dict[str, int] = defaultdict(int)
        for segment in draft.segments:
            activity[segment.user_id] += 1
        
        # Pick lowest activity, break ties by user_id for determinism
        most_inactive = min(eligible, key=lambda u: (activity.get(u, 0), u))
        
        return RingRecommendation(
            recommended_to_user_id=most_inactive,
            reason=f"@{most_inactive} has been least active recently. Engage them to keep momentum!"
        )
    
    @staticmethod
    def _compute_wait_counts(draft_id: str) -> Dict[str, Dict[str, int]]:
        """Count wait mode suggestions and votes per user (if wait mode present)"""
        
        try:
            with get_db_session() as session:
                # Query wait_suggestions count
                from backend.core.database import wait_suggestions, wait_votes
                
                sugg_query = select(
                    wait_suggestions.c.author_user_id,
                    func.count(wait_suggestions.c.suggestion_id).label("count")
                ).where(
                    and_(
                        wait_suggestions.c.draft_id == draft_id,
                        wait_suggestions.c.status == "queued"
                    )
                ).group_by(wait_suggestions.c.author_user_id)
                
                sugg_results = session.execute(sugg_query).fetchall()
                
                # Query wait_votes count
                votes_query = select(
                    wait_votes.c.voter_user_id,
                    func.count(wait_votes.c.vote_id).label("count")
                ).where(
                    wait_votes.c.draft_id == draft_id
                ).group_by(wait_votes.c.voter_user_id)
                
                votes_results = session.execute(votes_query).fetchall()
                
                # Build result dict
                counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"suggestions": 0, "votes": 0})
                
                for user_id, count in sugg_results:
                    counts[user_id]["suggestions"] = count
                
                for user_id, count in votes_results:
                    counts[user_id]["votes"] = count
                
                return dict(counts)
        except Exception:
            # Wait mode tables may not exist or draft doesn't have wait artifacts
            return {}
