# backend/conftest.py
import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add backend root to PYTHONPATH
BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session")
def db_url():
    """
    Provide DATABASE_URL for tests.
    
    Returns the URL from environment, or None if not set.
    Tests can use this to conditionally enable persistence tests.
    """
    return os.getenv('DATABASE_URL')


@pytest.fixture(scope="session", autouse=True)
def create_tables(db_url):
    """
    Create all database tables before running tests.
    
    Runs once per test session if DATABASE_URL is set.
    """
    if not db_url:
        yield
        return
    
    from backend.core.database import create_all_tables
    create_all_tables()
    yield


@pytest.fixture(scope="function")
def reset_db(db_url):
    """
    Reset database tables before each test.
    
    Only runs if DATABASE_URL is set. Truncates all tables to ensure
    clean state between tests.
    """
    if not db_url:
        yield  # Skip if no database
        return
    
    from backend.core.database import get_engine, metadata
    from sqlalchemy import text
    
    engine = get_engine()
    
    # Truncate all tables (preserving structure)
    with engine.connect() as conn:
        # Get all table names
        table_names = [table.name for table in metadata.sorted_tables]
        
        # Truncate in reverse order to handle foreign keys
        for table_name in reversed(table_names):
            conn.execute(text(f'TRUNCATE TABLE {table_name} CASCADE'))
            conn.commit()
    
    yield
    
    # Cleanup after test (truncate again)
    with engine.connect() as conn:
        for table_name in reversed(table_names):
            conn.execute(text(f'TRUNCATE TABLE {table_name} CASCADE'))
            conn.commit()


@pytest.fixture(scope="function", autouse=True)
def clear_idempotency_keys(db_url):
    """
    Clear idempotency keys table before each test to prevent cross-test contamination.
    
    Each test should start with a clean slate.
    """
    if not db_url:
        yield  # Skip if no database
        return
    
    from backend.core.database import get_engine
    from sqlalchemy import text
    
    engine = get_engine()
    
    # Truncate idempotency_keys table before test
    with engine.connect() as conn:
        conn.execute(text('TRUNCATE TABLE idempotency_keys CASCADE'))
        conn.commit()
    
    yield
    
    # No need to cleanup after since we'll truncate again at start of next test

@pytest.fixture(scope="function", autouse=True)
def mock_entitlements_enforcement(request):
    """
    Mock entitlements enforcement for tests to avoid blocking on missing plans.
    
    Tests should be able to run without database setup for entitlements.
    Automatically applied to most tests, but NOT applied to entitlements test files
    that explicitly test enforcement behavior.
    """
    # Don't mock enforcement for files that test entitlements explicitly
    if "entitlement_enforcement" in request.node.fspath.strpath:
        yield  # Skip mocking, use real enforcement
        return
    
    from backend.features.entitlements.service import EnforcementStatus, EnforcementDecision
    
    def mock_enforce(
        user_id: str,
        entitlement_key: str,
        *,
        requested: int = 1,
        usage_key=None,
        now=None,
        window_days=None,
    ):
        # Allow all entitlements for test users (test_*, holder*, user_*, etc.)
        return EnforcementDecision(
            status=EnforcementStatus.ALLOW,
            entitlement_value=-1,  # Unlimited
            current_usage=0,
            remaining="unlimited",
            grace_remaining=100,
            plan_id="test-plan",
            override_applied=False,
        )
    
    with patch("backend.features.entitlements.service.enforce_entitlement", side_effect=mock_enforce):
        yield
