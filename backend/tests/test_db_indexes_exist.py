"""
Test that all required database indexes and constraints exist.

This test verifies that the DB schema includes proper indexes and constraints
for performance and data integrity (Phase 3.7).
"""

import pytest
from sqlalchemy import text, inspect
from backend.core.database import get_engine, create_all_tables


def test_analytics_events_indexes():
    """Verify analytics_events table has required indexes."""
    create_all_tables()  # Ensure tables exist
    
    engine = get_engine()
    inspector = inspect(engine)
    
    # Get all indexes on analytics_events
    indexes = {idx['name']: idx for idx in inspector.get_indexes('analytics_events')}
    
    # Check for required indexes
    assert 'idx_analytics_events_type_occurred' in indexes, \
        "Missing composite index on (event_type, occurred_at)"
    
    # Verify idempotency_key index exists (it's marked unique=True on the column)
    assert 'ix_analytics_events_idempotency_key' in indexes or \
           any('idempotency_key' in str(c) for c in inspector.get_unique_constraints('analytics_events')), \
        "Missing UNIQUE index on idempotency_key"


def test_idempotency_keys_indexes():
    """Verify idempotency_keys table has required indexes."""
    create_all_tables()
    
    engine = get_engine()
    inspector = inspect(engine)
    
    # Check for required composite index
    indexes = {idx['name']: idx for idx in inspector.get_indexes('idempotency_keys')}
    assert 'idx_idempotency_keys_scope_created' in indexes, \
        "Missing composite index on (scope, created_at)"


def test_drafts_indexes():
    """Verify drafts table has required indexes."""
    create_all_tables()
    
    engine = get_engine()
    inspector = inspect(engine)
    
    indexes = {idx['name']: idx for idx in inspector.get_indexes('drafts')}
    
    # Check for required composite indexes
    assert 'idx_drafts_creator_created' in indexes, \
        "Missing composite index on (created_by, created_at)"
    assert 'idx_drafts_published_updated' in indexes, \
        "Missing composite index on (published, updated_at)"


def test_draft_segments_indexes_and_constraints():
    """Verify draft_segments table has required indexes and constraints."""
    create_all_tables()
    
    engine = get_engine()
    inspector = inspect(engine)
    
    # Check for composite index
    indexes = {idx['name']: idx for idx in inspector.get_indexes('draft_segments')}
    assert 'idx_draft_segments_draft_position' in indexes, \
        "Missing composite index on (draft_id, position)"
    
    # Check for UNIQUE constraint on (draft_id, position)
    constraints = {c['name']: c for c in inspector.get_unique_constraints('draft_segments')}
    assert 'uq_draft_segments_draft_position' in constraints, \
        "Missing UNIQUE constraint on (draft_id, position)"


def test_draft_collaborators_indexes_and_constraints():
    """Verify draft_collaborators table has required indexes and constraints."""
    create_all_tables()
    
    engine = get_engine()
    inspector = inspect(engine)
    
    # Check for UNIQUE constraint on (draft_id, user_id)
    constraints = {c['name']: c for c in inspector.get_unique_constraints('draft_collaborators')}
    assert 'uq_draft_collaborators_draft_user' in constraints, \
        "Missing UNIQUE constraint on (draft_id, user_id)"
    
    # Check for composite index
    indexes = {idx['name']: idx for idx in inspector.get_indexes('draft_collaborators')}
    assert 'idx_draft_collaborators_draft_joined' in indexes, \
        "Missing composite index on (draft_id, joined_at)"


def test_ring_passes_indexes():
    """Verify ring_passes table has required indexes."""
    create_all_tables()
    
    engine = get_engine()
    inspector = inspect(engine)
    
    indexes = {idx['name']: idx for idx in inspector.get_indexes('ring_passes')}
    
    # Check for required composite index for draft queries
    assert 'idx_ring_passes_draft_passed' in indexes, \
        "Missing composite index on (draft_id, passed_at, id)"
    
    # Check for user lookup indexes
    assert 'idx_ring_passes_from_user' in indexes, \
        "Missing index on from_user"
    assert 'idx_ring_passes_to_user' in indexes, \
        "Missing index on to_user"


def test_index_scan_performance():
    """
    Test that get_draft() and related queries use indexes efficiently.
    
    This test verifies that we're not doing sequential scans on large tables.
    For now, just verify the indexes exist; query planning is tested via
    EXPLAIN ANALYZE in performance benchmarks.
    """
    create_all_tables()
    
    engine = get_engine()
    inspector = inspect(engine)
    
    # Verify all tables have at least one index (except surrogate key)
    required_indexes = {
        'analytics_events': ['idx_analytics_events_type_occurred'],
        'idempotency_keys': ['idx_idempotency_keys_scope_created'],
        'drafts': ['idx_drafts_creator_created', 'idx_drafts_published_updated'],
        'draft_segments': ['idx_draft_segments_draft_position'],
        'draft_collaborators': ['idx_draft_collaborators_draft_joined'],
        'ring_passes': ['idx_ring_passes_draft_passed', 'idx_ring_passes_from_user', 'idx_ring_passes_to_user'],
    }
    
    for table_name, expected_indexes in required_indexes.items():
        actual_indexes = {idx['name'] for idx in inspector.get_indexes(table_name)}
        for expected_idx in expected_indexes:
            assert expected_idx in actual_indexes, \
                f"Table {table_name}: missing index {expected_idx}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
