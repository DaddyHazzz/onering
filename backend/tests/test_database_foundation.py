"""
Test script to verify database foundation setup.

This tests:
1. Database connection
2. Table creation (idempotent)
3. Basic CRUD operations
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.core.database import (
    init_engine,
    create_all_tables,
    drop_all_tables,
    check_connection,
    get_db_session,
    idempotency_keys,
)
from sqlalchemy import select, insert


def test_database_foundation():
    """Test database foundation setup."""
    
    print("=" * 60)
    print("PART 1: DATABASE FOUNDATION TEST")
    print("=" * 60)
    
    # Step 1: Check connection
    print("\n[1/5] Checking database connection...")
    assert check_connection(), (
        "Database connection failed! "
        "Make sure PostgreSQL is running: "
        "docker-compose -f infra/docker-compose.yml up -d postgres"
    )
    print("✅ Database connection successful")
    
    # Step 2: Create tables (idempotent)
    print("\n[2/5] Creating tables (idempotent)...")
    try:
        create_all_tables()
        print("✅ Tables created successfully")
    except Exception as e:
        raise AssertionError(f"Failed to create tables: {e}")
    
    # Step 3: Test idempotency keys table
    print("\n[3/5] Testing idempotency keys table...")
    try:
        with get_db_session() as session:
            # Insert a test key
            test_key = "test_key_12345"
            stmt = insert(idempotency_keys).values(
                key=test_key,
                scope="test"
            )
            session.execute(stmt)
            session.commit()
            
            # Query it back
            result = session.execute(
                select(idempotency_keys).where(idempotency_keys.c.key == test_key)
            ).first()
            
            assert result and result.key == test_key, "Failed to retrieve idempotency key"
            print(f"✅ Idempotency key inserted and retrieved: {result.key}")
            
            # Clean up
            session.execute(
                idempotency_keys.delete().where(idempotency_keys.c.key == test_key)
            )
            session.commit()
            
    except Exception as e:
        raise AssertionError(f"Idempotency keys test failed: {e}")
    
    # Step 4: Test duplicate key rejection
    print("\n[4/5] Testing duplicate key rejection...")
    try:
        with get_db_session() as session:
            test_key = "duplicate_test_key"
            
            # Insert first time
            stmt = insert(idempotency_keys).values(
                key=test_key,
                scope="test"
            )
            session.execute(stmt)
            session.commit()
        
        # Try to insert again (should fail)
        try:
            with get_db_session() as session:
                stmt = insert(idempotency_keys).values(
                    key=test_key,
                    scope="test"
                )
                session.execute(stmt)
                session.commit()
            
            raise AssertionError("Duplicate key was not rejected!")
        except AssertionError:
            raise
        except Exception:
            print("✅ Duplicate key correctly rejected")
        
        # Clean up
        with get_db_session() as session:
            session.execute(
                idempotency_keys.delete().where(idempotency_keys.c.key == test_key)
            )
            session.commit()
            
    except AssertionError:
        raise
    except Exception as e:
        raise AssertionError(f"Duplicate key test failed: {e}")
    
    # Step 5: Verify all expected tables exist
    print("\n[5/5] Verifying all tables exist...")
    expected_tables = [
        'analytics_events',
        'idempotency_keys',
        'drafts',
        'draft_segments',
        'draft_collaborators',
        'ring_passes',
    ]
    
    try:
        from sqlalchemy import inspect
        engine = init_engine()
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        missing_tables = [t for t in expected_tables if t not in existing_tables]
        
        assert not missing_tables, f"Missing tables: {missing_tables}"
        
        print(f"✅ All {len(expected_tables)} tables exist:")
        for table in expected_tables:
            print(f"   - {table}")
    except Exception as e:
        raise AssertionError(f"Table verification failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ PART 1 COMPLETE: Database foundation is ready")
    print("=" * 60)
    # Test passed - pytest will capture this


if __name__ == "__main__":
    # Set DATABASE_URL if not set
    if not os.getenv("DATABASE_URL"):
        os.environ["DATABASE_URL"] = "postgresql://onering:onering@localhost:5432/onering"
    
    success = test_database_foundation()
    sys.exit(0 if success else 1)
