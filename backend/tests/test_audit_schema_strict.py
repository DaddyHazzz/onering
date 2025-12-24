"""
Test that SQLite in-memory schema includes all Phase 4.6 audit columns (Phase 4.6.1).

CRITICAL: This test ensures that the billing_admin_audit table has ALL required columns
for Phase 4.6.1. If this test fails, audit writes may fail at runtime (500 error).
"""

import pytest
from sqlalchemy import create_engine, MetaData, text, inspect
from sqlalchemy.pool import StaticPool

from backend.core.database import metadata


def test_audit_schema_has_all_required_columns():
    """
    Ensure SQLite in-memory database includes ALL Phase 4.6 audit columns.
    
    Required columns:
    - id (PK)
    - actor (legacy)
    - actor_id (Phase 4.6)
    - actor_type (Phase 4.6)
    - actor_email (Phase 4.6)
    - auth_mechanism (Phase 4.6)
    - action
    - target_user_id
    - target_resource
    - payload_json
    - created_at
    """
    # Create SQLite in-memory engine with StaticPool (same as test fixtures)
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    
    # Create all tables from the canonical schema
    metadata.create_all(engine)
    
    # Inspect the table
    inspector = inspect(engine)
    columns = inspector.get_columns('billing_admin_audit')
    column_names = {col['name'] for col in columns}
    
    # Assert all required columns exist
    required = {
        'id', 'actor', 'actor_id', 'actor_type', 'actor_email', 'auth_mechanism',
        'action', 'target_user_id', 'target_resource', 'payload_json', 'created_at'
    }
    
    missing = required - column_names
    if missing:
        pytest.fail(f"billing_admin_audit is missing columns: {missing}. Found: {column_names}")
    
    # Verify actor_id is nullable (for legacy compatibility)
    actor_id_col = next((col for col in columns if col['name'] == 'actor_id'), None)
    assert actor_id_col is not None, "actor_id column not found"
    assert actor_id_col['nullable'], "actor_id should be nullable (Phase 4.6 backward compat)"
    
    # Verify actor_type is nullable
    actor_type_col = next((col for col in columns if col['name'] == 'actor_type'), None)
    assert actor_type_col is not None, "actor_type column not found"
    assert actor_type_col['nullable'], "actor_type should be nullable"
    
    # Verify auth_mechanism is nullable
    auth_mech_col = next((col for col in columns if col['name'] == 'auth_mechanism'), None)
    assert auth_mech_col is not None, "auth_mechanism column not found"
    assert auth_mech_col['nullable'], "auth_mechanism should be nullable"


def test_audit_table_can_insert_with_all_phase_46_columns():
    """
    Test that we can insert a row with all Phase 4.6 audit columns.
    This ensures the INSERT statement in create_audit_log will work.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    metadata.create_all(engine)
    
    # Try to insert a row with all Phase 4.6 fields
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO billing_admin_audit (
                actor, actor_id, actor_type, actor_email, auth_mechanism,
                action, target_user_id, target_resource, payload_json
            )
            VALUES (
                :actor, :actor_id, :actor_type, :actor_email, :auth_mechanism,
                :action, :target_user_id, :target_resource, :payload_json
            )
        """), {
            'actor': 'user-xyz123',
            'actor_id': 'user-xyz123',
            'actor_type': 'clerk',
            'actor_email': 'test@example.com',
            'auth_mechanism': 'clerk_jwt',
            'action': 'test_action',
            'target_user_id': 'target-123',
            'target_resource': 'stripe_sub_123',
            'payload_json': '{"test": "data"}'
        })
        conn.commit()
        
        # Verify the row exists
        result = conn.execute(text("SELECT COUNT(*) as cnt FROM billing_admin_audit"))
        count = result.scalar()
        assert count == 1, f"Expected 1 row, got {count}"


def test_audit_table_indexes_created():
    """
    Verify that all Phase 4.6 indexes were created.
    Indexes are critical for audit log queries (by actor_id, by action, by created_at).
    """
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False}
    )
    metadata.create_all(engine)
    
    inspector = inspect(engine)
    indexes = inspector.get_indexes('billing_admin_audit')
    index_names = {idx['name'] for idx in indexes}
    
    # Verify critical indexes exist
    critical_indexes = {
        'idx_billing_admin_audit_actor_id',
        'idx_billing_admin_audit_action',
        'idx_billing_admin_audit_created_at'
    }
    
    missing_indexes = critical_indexes - index_names
    if missing_indexes:
        pytest.fail(f"Missing critical indexes: {missing_indexes}. Found: {index_names}")
