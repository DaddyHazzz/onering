"""
Test billing schema tables (Phase 4.3).

Verifies billing_customers, billing_subscriptions, and billing_events tables
exist with correct columns, indexes, and constraints.
"""
import pytest
from sqlalchemy import inspect
from backend.core.database import (
    get_engine,
    billing_customers,
    billing_subscriptions,
    billing_events,
)


def test_billing_customers_table_exists():
    """Verify billing_customers table exists with correct structure."""
    engine = get_engine()
    inspector = inspect(engine)
    
    assert "billing_customers" in inspector.get_table_names()
    
    columns = {col["name"]: col for col in inspector.get_columns("billing_customers")}
    
    # Required columns
    assert "id" in columns
    assert "user_id" in columns
    assert "stripe_customer_id" in columns
    assert "created_at" in columns
    assert "updated_at" in columns
    
    # Verify nullability
    assert columns["user_id"]["nullable"] is False
    assert columns["stripe_customer_id"]["nullable"] is False


def test_billing_customers_indexes():
    """Verify billing_customers has required indexes."""
    engine = get_engine()
    inspector = inspect(engine)
    
    indexes = {idx["name"]: idx for idx in inspector.get_indexes("billing_customers")}
    
    # Should have indexes on user_id and stripe_customer_id
    assert any("user_id" in str(idx) for idx in indexes.values())
    assert any("stripe_customer_id" in str(idx) or "stripe_id" in str(idx) for idx in indexes.values())


def test_billing_customers_unique_constraints():
    """Verify billing_customers enforces uniqueness."""
    engine = get_engine()
    inspector = inspect(engine)
    
    # user_id and stripe_customer_id should be unique
    unique_constraints = inspector.get_unique_constraints("billing_customers")
    pk_constraint = inspector.get_pk_constraint("billing_customers")
    
    # Either explicit unique constraints or unique indexes
    indexes = inspector.get_indexes("billing_customers")
    unique_indexes = [idx for idx in indexes if idx.get("unique", False)]
    
    # Check user_id uniqueness
    user_id_unique = any(
        "user_id" in constraint.get("column_names", [])
        for constraint in unique_constraints
    ) or any(
        "user_id" in idx.get("column_names", [])
        for idx in unique_indexes
    )
    
    # Check stripe_customer_id uniqueness
    stripe_id_unique = any(
        "stripe_customer_id" in constraint.get("column_names", [])
        for constraint in unique_constraints
    ) or any(
        "stripe_customer_id" in idx.get("column_names", [])
        for idx in unique_indexes
    )
    
    assert user_id_unique, "user_id should be unique"
    assert stripe_id_unique, "stripe_customer_id should be unique"


def test_billing_subscriptions_table_exists():
    """Verify billing_subscriptions table exists with correct structure."""
    engine = get_engine()
    inspector = inspect(engine)
    
    assert "billing_subscriptions" in inspector.get_table_names()
    
    columns = {col["name"]: col for col in inspector.get_columns("billing_subscriptions")}
    
    # Required columns
    assert "id" in columns
    assert "user_id" in columns
    assert "stripe_subscription_id" in columns
    assert "plan_id" in columns
    assert "status" in columns
    assert "current_period_end" in columns
    assert "cancel_at_period_end" in columns
    assert "created_at" in columns
    assert "updated_at" in columns
    
    # Verify nullability
    assert columns["user_id"]["nullable"] is False
    assert columns["stripe_subscription_id"]["nullable"] is False
    assert columns["plan_id"]["nullable"] is False
    assert columns["status"]["nullable"] is False
    assert columns["cancel_at_period_end"]["nullable"] is False


def test_billing_subscriptions_indexes():
    """Verify billing_subscriptions has required indexes."""
    engine = get_engine()
    inspector = inspect(engine)
    
    indexes = {idx["name"]: idx for idx in inspector.get_indexes("billing_subscriptions")}
    
    # Should have indexes on user_id, stripe_subscription_id, and status
    assert any("user_id" in str(idx) for idx in indexes.values())
    assert any("stripe_subscription_id" in str(idx) or "stripe_id" in str(idx) for idx in indexes.values())
    assert any("status" in str(idx) for idx in indexes.values())


def test_billing_events_table_exists():
    """Verify billing_events table exists with correct structure."""
    engine = get_engine()
    inspector = inspect(engine)
    
    assert "billing_events" in inspector.get_table_names()
    
    columns = {col["name"]: col for col in inspector.get_columns("billing_events")}
    
    # Required columns
    assert "id" in columns
    assert "stripe_event_id" in columns
    assert "event_type" in columns
    assert "received_at" in columns
    assert "payload_hash" in columns
    assert "processed" in columns
    assert "processed_at" in columns
    assert "error" in columns
    
    # Verify nullability
    assert columns["stripe_event_id"]["nullable"] is False
    assert columns["event_type"]["nullable"] is False
    assert columns["received_at"]["nullable"] is False
    assert columns["payload_hash"]["nullable"] is False
    assert columns["processed"]["nullable"] is False


def test_billing_events_unique_stripe_event_id():
    """Verify billing_events enforces stripe_event_id uniqueness (idempotency)."""
    engine = get_engine()
    inspector = inspect(engine)
    
    unique_constraints = inspector.get_unique_constraints("billing_events")
    indexes = inspector.get_indexes("billing_events")
    unique_indexes = [idx for idx in indexes if idx.get("unique", False)]
    
    # stripe_event_id should be unique
    stripe_event_unique = any(
        "stripe_event_id" in constraint.get("column_names", [])
        for constraint in unique_constraints
    ) or any(
        "stripe_event_id" in idx.get("column_names", [])
        for idx in unique_indexes
    )
    
    assert stripe_event_unique, "stripe_event_id should be unique for idempotency"


def test_billing_events_indexes():
    """Verify billing_events has required indexes."""
    engine = get_engine()
    inspector = inspect(engine)
    
    indexes = {idx["name"]: idx for idx in inspector.get_indexes("billing_events")}
    
    # Should have indexes on stripe_event_id, received_at, and processed
    assert any("stripe_event_id" in str(idx) for idx in indexes.values())
    assert any("received_at" in str(idx) for idx in indexes.values())
    assert any("processed" in str(idx) for idx in indexes.values())


def test_billing_tables_can_query_without_errors():
    """Integration test: verify billing tables can be queried."""
    from sqlalchemy import select
    from backend.core.database import get_db_session
    
    with get_db_session() as session:
        # Query should succeed even if empty
        result = session.execute(select(billing_customers)).fetchall()
        assert isinstance(result, list)
        
        result = session.execute(select(billing_subscriptions)).fetchall()
        assert isinstance(result, list)
        
        result = session.execute(select(billing_events)).fetchall()
        assert isinstance(result, list)
