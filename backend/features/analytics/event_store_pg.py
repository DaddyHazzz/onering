"""
backend/features/analytics/event_store_pg.py

PostgreSQL-backed append-only event store for analytics (Phase 3.5).

This module provides persistent storage for events while maintaining:
- Append-only semantics
- Idempotency guarantees
- Deterministic ordering
- Reducer compatibility
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import select, insert, and_
from sqlalchemy.exc import IntegrityError

from backend.core.database import get_db_session, analytics_events
from backend.features.analytics.event_store import Event


class PostgresEventStore:
    """
    PostgreSQL-backed event store.
    
    Maintains identical interface to in-memory EventStore.
    """
    
    @staticmethod
    def append(event: Event, idempotency_key: str) -> bool:
        """
        Append event to PostgreSQL with idempotency guarantee.
        
        Args:
            event: Event to append
            idempotency_key: Unique key to prevent duplicate processing
        
        Returns:
            True if event was appended, False if key already seen
        """
        try:
            with get_db_session() as session:
                # Convert event to database row
                stmt = insert(analytics_events).values(
                    event_type=event.event_type,
                    payload=event.data,
                    occurred_at=event.timestamp,
                    idempotency_key=idempotency_key,
                )
                
                session.execute(stmt)
                session.commit()
                return True
                
        except IntegrityError:
            # Duplicate idempotency key
            return False
    
    @staticmethod
    def get_events(
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_type: Optional[str] = None
    ) -> List[Event]:
        """
        Retrieve events from PostgreSQL in time window.
        
        Args:
            start_time: Start of time window (inclusive, optional)
            end_time: End of time window (inclusive, optional)
            event_type: Filter by event type (optional)
        
        Returns:
            List of Event instances (always copies, not DB references)
        """
        with get_db_session() as session:
            # Build query with filters
            query = select(analytics_events)
            
            filters = []
            if start_time:
                filters.append(analytics_events.c.occurred_at >= start_time)
            if end_time:
                filters.append(analytics_events.c.occurred_at <= end_time)
            if event_type:
                filters.append(analytics_events.c.event_type == event_type)
            
            if filters:
                query = query.where(and_(*filters))
            
            # Order by occurred_at, then id for deterministic ordering
            query = query.order_by(
                analytics_events.c.occurred_at,
                analytics_events.c.id
            )
            
            # Execute query
            result = session.execute(query)
            
            # Convert rows to Event objects (copies, not references)
            events = []
            for row in result:
                event = Event(
                    event_type=row.event_type,
                    timestamp=row.occurred_at,
                    data=dict(row.payload) if row.payload else {}
                )
                events.append(event)
            
            return events
    
    @staticmethod
    def clear() -> None:
        """
        Clear all events from PostgreSQL.
        FOR TESTING ONLY.
        """
        with get_db_session() as session:
            session.execute(analytics_events.delete())
            session.commit()
    
    @staticmethod
    def count() -> int:
        """Return total number of events in PostgreSQL."""
        with get_db_session() as session:
            result = session.execute(
                select(analytics_events.c.id)
            )
            return len(result.all())
    
    @staticmethod
    def check_idempotency(idempotency_key: str) -> bool:
        """
        Check if idempotency key has been seen before.
        
        Args:
            idempotency_key: Key to check
        
        Returns:
            True if key already exists, False otherwise
        """
        with get_db_session() as session:
            result = session.execute(
                select(analytics_events.c.id).where(
                    analytics_events.c.idempotency_key == idempotency_key
                )
            ).first()
            
            return result is not None


def migrate_in_memory_to_postgres(in_memory_store) -> int:
    """
    Migrate events from in-memory store to PostgreSQL.
    
    This is a one-time migration helper for Phase 3.5 rollout.
    
    Args:
        in_memory_store: Instance of in-memory EventStore
    
    Returns:
        Number of events migrated
    """
    from backend.features.analytics.event_store import EventStore as InMemoryStore
    
    # Get all events from in-memory store
    events = in_memory_store.get_events()
    
    migrated_count = 0
    pg_store = PostgresEventStore()
    
    for event in events:
        # Generate idempotency key for each event
        # Use event data to create unique key
        key_parts = [event.event_type, str(event.timestamp.isoformat())]
        
        # Add relevant data fields to key
        if event.data:
            for k, v in sorted(event.data.items()):
                key_parts.append(f"{k}={v}")
        
        idempotency_key = ":".join(key_parts)
        
        # Attempt to append
        if pg_store.append(event, idempotency_key):
            migrated_count += 1
    
    return migrated_count
