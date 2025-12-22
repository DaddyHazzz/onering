"""
Database configuration and connection management.

This module provides:
- SQLAlchemy engine and session management
- Connection pooling with sane defaults
- Test database support
- Migration utilities
"""
from typing import Optional
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean, JSON, Text, Index, ForeignKey, UniqueConstraint
from sqlalchemy.pool import QueuePool
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.sql import func
import os

from backend.core.config import settings


# SQLAlchemy metadata for table definitions
metadata = MetaData()

# Connection pooling configuration
POOL_SIZE = 10
MAX_OVERFLOW = 20
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600  # Recycle connections after 1 hour

# Global engine and session factory
_engine = None
_SessionLocal = None


def get_database_url() -> Optional[str]:
    """
    Get the database URL from settings or environment.
    
    For testing, use TEST_DATABASE_URL if available.
    """
    test_url = os.getenv("TEST_DATABASE_URL")
    if test_url:
        return test_url
    
    return settings.DATABASE_URL


def init_engine(database_url: Optional[str] = None):
    """
    Initialize the SQLAlchemy engine.
    
    Args:
        database_url: Optional override for DATABASE_URL
    """
    global _engine, _SessionLocal
    
    url = database_url or get_database_url()
    
    if not url:
        raise ValueError(
            "DATABASE_URL is not configured. "
            "Set DATABASE_URL in environment or .env file."
        )
    
    # Create engine with connection pooling
    _engine = create_engine(
        url,
        poolclass=QueuePool,
        pool_size=POOL_SIZE,
        max_overflow=MAX_OVERFLOW,
        pool_timeout=POOL_TIMEOUT,
        pool_recycle=POOL_RECYCLE,
        echo=False,  # Set to True for SQL query logging
    )
    
    # Create session factory
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine
    )
    
    return _engine


def get_engine():
    """Get the current SQLAlchemy engine."""
    global _engine
    if _engine is None:
        init_engine()
    return _engine


def get_session_factory():
    """Get the session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        init_engine()
    return _SessionLocal


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_session() as session:
            session.execute(...)
            session.commit()
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all_tables():
    """
    Create all tables defined in metadata.
    
    This is idempotent - tables that already exist will not be recreated.
    """
    engine = get_engine()
    metadata.create_all(bind=engine)


def drop_all_tables():
    """
    Drop all tables defined in metadata.
    
    WARNING: This is destructive! Only use in tests or development.
    """
    engine = get_engine()
    metadata.drop_all(bind=engine)


def reset_database():
    """
    Reset the database by dropping and recreating all tables.
    
    WARNING: This is destructive! Only use in tests.
    """
    drop_all_tables()
    create_all_tables()


def ensure_constraints_and_indexes():
    """
    Ensure all required constraints and indexes exist.
    
    This is idempotent: safe to call multiple times.
    
    Uses CREATE INDEX IF NOT EXISTS for indexes and verifies
    UNIQUE constraints are in place (via table definitions).
    """
    engine = get_engine()
    
    # Constraints are handled by metadata.create_all() in table definitions
    # Indexes are created by SQLAlchemy's Index objects in table definitions
    # Both are idempotent as long as "create_all_tables()" is called first
    
    # Simply ensure all tables and indexes from metadata exist
    create_all_tables()


def check_connection() -> bool:
    """
    Check if database connection is available.
    
    Returns:
        True if connection successful, False otherwise
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(func.now())
        return True
    except Exception as e:
        print(f"Database connection check failed: {e}")
        return False


# Table definitions will be added here as we migrate features

# Analytics events table (for Phase 3.5)
analytics_events = Table(
    'analytics_events',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('event_type', String(100), nullable=False, index=True),
    Column('payload', JSON, nullable=False),
    Column('occurred_at', DateTime(timezone=True), nullable=False, index=True),
    Column('idempotency_key', String(255), unique=True, nullable=False, index=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    # Composite index for common filtering pattern: (event_type, occurred_at)
    Index('idx_analytics_events_type_occurred', 'event_type', 'occurred_at'),
)

# Idempotency keys table
idempotency_keys = Table(
    'idempotency_keys',
    metadata,
    Column('key', String(255), primary_key=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('scope', String(100), nullable=True, index=True),
    # Composite index for scope + created_at lookups
    Index('idx_idempotency_keys_scope_created', 'scope', 'created_at'),
)

# Collaboration drafts table
drafts = Table(
    'drafts',
    metadata,
    Column('id', String(100), primary_key=True),
    Column('created_by', String(100), nullable=False, index=True),
    Column('title', Text, nullable=False),
    Column('description', Text, nullable=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    Column('published', Boolean, default=False, nullable=False, index=True),
    Column('published_at', DateTime(timezone=True), nullable=True),
    Column('view_count', Integer, default=0, nullable=False),
    # Composite index for list_user_drafts pattern: (created_by, created_at)
    Index('idx_drafts_creator_created', 'created_by', 'created_at'),
    # Index for published draft queries
    Index('idx_drafts_published_updated', 'published', 'updated_at'),
)

# Draft segments table
draft_segments = Table(
    'draft_segments',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('draft_id', String(100), nullable=False, index=True),
    Column('author', String(100), nullable=False, index=True),
    Column('content', Text, nullable=False),
    Column('position', Integer, nullable=False),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    # Composite index for get_draft pattern: (draft_id, position) for ordering
    Index('idx_draft_segments_draft_position', 'draft_id', 'position'),
    # Unique constraint: (draft_id, position) to prevent duplicate positions
    UniqueConstraint('draft_id', 'position', name='uq_draft_segments_draft_position'),
)

# Draft collaborators table
draft_collaborators = Table(
    'draft_collaborators',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('draft_id', String(100), nullable=False, index=True),
    Column('user_id', String(100), nullable=False, index=True),
    Column('role', String(50), nullable=False),  # 'owner', 'editor', 'viewer'
    Column('joined_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    # Unique constraint: one collaborator role per (draft_id, user_id)
    UniqueConstraint('draft_id', 'user_id', name='uq_draft_collaborators_draft_user'),
    # Composite index for finding collaborators by draft
    Index('idx_draft_collaborators_draft_joined', 'draft_id', 'joined_at'),
)

# Ring passes table
ring_passes = Table(
    'ring_passes',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('draft_id', String(100), nullable=False, index=True),
    Column('from_user', String(100), nullable=False, index=True),
    Column('to_user', String(100), nullable=False, index=True),
    Column('passed_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    # Composite index for finding ring history by draft with ordering
    Index('idx_ring_passes_draft_passed', 'draft_id', 'passed_at', 'id'),
    # Indexes for querying by user (from/to)
    Index('idx_ring_passes_from_user', 'from_user'),
    Index('idx_ring_passes_to_user', 'to_user'),
)
