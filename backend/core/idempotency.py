"""
backend/core/idempotency.py
Global idempotency key management for all services.
"""

import os
from datetime import datetime, timezone
from sqlalchemy import select
from backend.core.database import get_db_session, idempotency_keys

# In-memory fallback
_in_memory_keys: set = set()


def check_and_set(key: str, operation: str = "generic") -> bool:
    """
    Check if idempotency key exists, and set it if not (atomic).
    
    Args:
        key: Idempotency key string
        operation: Operation type (for debugging/monitoring)
    
    Returns:
        True if key was already seen (duplicate request)
        False if key is new (first time seeing it)
    """
    if os.getenv('DATABASE_URL'):
        # Use PostgreSQL
        from sqlalchemy.exc import IntegrityError
        from backend.core.database import get_session_factory
        
        SessionLocal = get_session_factory()
        session = SessionLocal()
        try:
            # Try to insert new key
            session.execute(
                idempotency_keys.insert().values(
                    key=key,
                    scope=operation,  # Column name is 'scope' not 'operation'
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
            return False  # First time (insert succeeded)
        except IntegrityError:
            # Duplicate key - UNIQUE constraint violation
            session.rollback()
            return True  # Already seen
        except Exception:
            session.rollback()
            # On unexpected error, assume not seen to avoid blocking requests
            return False
        finally:
            session.close()
    else:
        # Use in-memory fallback
        if key in _in_memory_keys:
            return True
        _in_memory_keys.add(key)
        return False


def check_key(key: str) -> bool:
    """
    Check if idempotency key exists (read-only).
    
    Args:
        key: Idempotency key string
    
    Returns:
        True if key exists, False otherwise
    """
    if os.getenv('DATABASE_URL'):
        try:
            with get_db_session() as session:
                result = session.execute(
                    select(idempotency_keys.c.key).where(
                        idempotency_keys.c.key == key
                    )
                ).first()
                return result is not None
        except Exception:
            return False
    else:
        return key in _in_memory_keys


def clear_all_keys() -> None:
    """Clear all idempotency keys (testing only)."""
    global _in_memory_keys
    if os.getenv('DATABASE_URL'):
        try:
            with get_db_session() as session:
                session.execute(idempotency_keys.delete())
                session.commit()
        except Exception:
            pass
    _in_memory_keys.clear()
