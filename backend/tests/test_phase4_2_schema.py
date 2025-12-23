"""
Test Phase 4.2 schema verification.

Ensures entitlement_overrides, entitlement_grace_usage, and enforcement columns
exist in the database without relying on import-time side effects.
"""
import pytest
from sqlalchemy import inspect, text
from backend.core.database import get_engine, create_all_tables


@pytest.fixture(scope="function", autouse=True)
def ensure_schema():
    """Ensure schema is created before tests."""
    create_all_tables()
    yield


class TestPhase42Schema:
    """Verify Phase 4.2 schema additions."""

    def test_plans_table_has_enforcement_columns(self):
        """Verify plans table has enforcement_enabled and enforcement_grace_count."""
        engine = get_engine()
        inspector = inspect(engine)
        
        columns = {col['name'] for col in inspector.get_columns('plans')}
        assert 'enforcement_enabled' in columns, "plans.enforcement_enabled column missing"
        assert 'enforcement_grace_count' in columns, "plans.enforcement_grace_count column missing"

    def test_entitlement_overrides_table_exists(self):
        """Verify entitlement_overrides table exists with required columns."""
        engine = get_engine()
        inspector = inspect(engine)
        
        tables = inspector.get_table_names()
        assert 'entitlement_overrides' in tables, "entitlement_overrides table missing"
        
        columns = {col['name'] for col in inspector.get_columns('entitlement_overrides')}
        required = {'id', 'user_id', 'entitlement_key', 'override_value', 'reason', 'expires_at', 'created_by', 'created_at'}
        assert required.issubset(columns), f"entitlement_overrides missing columns: {required - columns}"

    def test_entitlement_grace_usage_table_exists(self):
        """Verify entitlement_grace_usage table exists with required columns."""
        engine = get_engine()
        inspector = inspect(engine)
        
        tables = inspector.get_table_names()
        assert 'entitlement_grace_usage' in tables, "entitlement_grace_usage table missing"
        
        columns = {col['name'] for col in inspector.get_columns('entitlement_grace_usage')}
        required = {'id', 'user_id', 'plan_id', 'entitlement_key', 'used', 'updated_at'}
        assert required.issubset(columns), f"entitlement_grace_usage missing columns: {required - columns}"

    def test_entitlement_overrides_unique_constraint_exists(self):
        """Verify unique constraint on (user_id, entitlement_key)."""
        engine = get_engine()
        inspector = inspect(engine)
        
        constraints = inspector.get_unique_constraints('entitlement_overrides')
        constraint_names = {c['name'] for c in constraints}
        
        # Check that at least one constraint covers (user_id, entitlement_key)
        has_unique = any(
            'user_id' in c['column_names'] and 'entitlement_key' in c['column_names']
            for c in constraints
        )
        assert has_unique, "No unique constraint on (user_id, entitlement_key)"

    def test_entitlement_grace_usage_unique_constraint_exists(self):
        """Verify unique constraint on (user_id, plan_id, entitlement_key)."""
        engine = get_engine()
        inspector = inspect(engine)
        
        constraints = inspector.get_unique_constraints('entitlement_grace_usage')
        
        has_unique = any(
            set(c['column_names']) == {'user_id', 'plan_id', 'entitlement_key'}
            for c in constraints
        )
        assert has_unique, "No unique constraint on (user_id, plan_id, entitlement_key)"

    def test_query_enforcement_columns_succeeds(self):
        """Verify we can query enforcement columns without errors."""
        engine = get_engine()
        
        # This should not raise UndefinedColumn or similar
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT enforcement_enabled, enforcement_grace_count FROM plans LIMIT 1")
            ).fetchone()
            # Result may be None if no plans, but query should succeed
