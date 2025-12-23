# backend/conftest.py
import sys
import os
import pytest
from pathlib import Path

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
