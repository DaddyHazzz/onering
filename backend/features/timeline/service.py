"""Timeline service: aggregate audit logs into timeline events.

Phase 8.3: Collaboration history and attribution tracking.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
from collections import defaultdict

from sqlalchemy import select, and_, desc, asc
from backend.core.database import get_db_session, audit_events
from backend.core.tracing import start_span
from backend.features.timeline.models import (
    TimelineEvent,
    TimelineResponse,
    ContributorStats,
    AttributionResponse,
)
from backend.features.timeline.mapping import map_audit_to_timeline

logger = logging.getLogger(__name__)


class TimelineService:
    """Service for timeline aggregation and attribution tracking."""
    
    def get_timeline(
        self,
        draft_id: str,
        limit: int = 200,
        cursor: Optional[str] = None,
        asc_order: bool = True
    ) -> TimelineResponse:
        """Get timeline events for a draft.
        
        Args:
            draft_id: Draft ID to fetch timeline for
            limit: Maximum events to return (max 500)
            cursor: Pagination cursor (event_id to start after)
            asc_order: Sort ascending (oldest first) if True, descending if False
        
        Returns:
            TimelineResponse with events and optional next_cursor
        """
        with start_span("timeline.get_timeline", {"draft_id": draft_id, "limit": limit}):
            # Clamp limit
            limit = min(limit, 500)
            
            try:
                with get_db_session() as session:
                    # Build query
                    query = select(audit_events).where(
                        audit_events.c.draft_id == draft_id
                    )
                    
                    # Apply cursor pagination if provided
                    if cursor:
                        try:
                            cursor_id = int(cursor)
                            if asc_order:
                                query = query.where(audit_events.c.id > cursor_id)
                            else:
                                query = query.where(audit_events.c.id < cursor_id)
                        except ValueError:
                            logger.warning(f"Invalid cursor format: {cursor}")
                    
                    # Apply ordering
                    if asc_order:
                        query = query.order_by(asc(audit_events.c.ts))
                    else:
                        query = query.order_by(desc(audit_events.c.ts))
                    
                    # Apply limit (fetch +1 to check for next page)
                    query = query.limit(limit + 1)
                    
                    # Execute query
                    result = session.execute(query)
                    rows = result.fetchall()
                    
                    # Convert to dictionaries
                    audit_records = []
                    for row in rows[:limit]:  # Only take 'limit' items
                        audit_records.append({
                            "id": row.id,
                            "ts": row.ts,
                            "user_id": row.user_id,
                            "action": row.action,
                            "draft_id": row.draft_id,
                            "metadata": row.metadata or {},
                        })
                    
                    # Map to timeline events
                    events = [map_audit_to_timeline(record) for record in audit_records]
                    
                    # Determine next cursor
                    next_cursor = None
                    if len(rows) > limit:
                        # There are more items
                        last_event_id = audit_records[-1]["id"]
                        next_cursor = str(last_event_id)
                    
                    return TimelineResponse(
                        draft_id=draft_id,
                        events=events,
                        next_cursor=next_cursor
                    )
            
            except Exception as e:
                logger.error(f"Error fetching timeline for draft {draft_id}: {e}")
                # Return empty timeline on error
                return TimelineResponse(draft_id=draft_id, events=[], next_cursor=None)
    
    def get_attribution(self, draft_id: str) -> AttributionResponse:
        """Get contributor attribution for a draft.
        
        Aggregates segment_added events by user_id to show who contributed what.
        
        Args:
            draft_id: Draft ID to fetch attribution for
        
        Returns:
            AttributionResponse with contributor stats
        """
        with start_span("timeline.get_attribution", {"draft_id": draft_id}):
            try:
                with get_db_session() as session:
                    # Query all segment_added events for this draft
                    query = select(audit_events).where(
                        and_(
                            audit_events.c.draft_id == draft_id,
                            audit_events.c.action == "segment_added"
                        )
                    ).order_by(asc(audit_events.c.ts))
                    
                    result = session.execute(query)
                    rows = result.fetchall()
                    
                    # Aggregate by user_id
                    user_contributions = defaultdict(lambda: {
                        "segment_count": 0,
                        "segment_ids": [],
                        "timestamps": []
                    })
                    
                    for row in rows:
                        user_id = row.user_id
                        if not user_id:
                            continue
                        
                        metadata = row.metadata or {}
                        segment_id = metadata.get("segment_id")
                        
                        user_contributions[user_id]["segment_count"] += 1
                        if segment_id:
                            user_contributions[user_id]["segment_ids"].append(segment_id)
                        user_contributions[user_id]["timestamps"].append(row.ts)
                    
                    # Build contributor stats
                    contributors = []
                    for user_id, data in user_contributions.items():
                        if not data["timestamps"]:
                            continue
                        
                        contributors.append(ContributorStats(
                            user_id=user_id,
                            segment_count=data["segment_count"],
                            segment_ids=data["segment_ids"],
                            first_ts=min(data["timestamps"]),
                            last_ts=max(data["timestamps"])
                        ))
                    
                    # Sort by segment_count descending (most prolific first)
                    contributors.sort(key=lambda c: c.segment_count, reverse=True)
                    
                    return AttributionResponse(
                        draft_id=draft_id,
                        contributors=contributors
                    )
            
            except Exception as e:
                logger.error(f"Error fetching attribution for draft {draft_id}: {e}")
                return AttributionResponse(draft_id=draft_id, contributors=[])


# Singleton service instance
timeline_service = TimelineService()
