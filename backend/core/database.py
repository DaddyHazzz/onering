"""
Database configuration and connection management.

This module provides:
- SQLAlchemy engine and session management
- Connection pooling with sane defaults
- Test database support
- Migration utilities
"""
from typing import Optional, Generator
from contextlib import contextmanager
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Boolean, JSON, Text, Index, ForeignKey, UniqueConstraint, text
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


def get_db() -> Generator[Session, None, None]:
    """FastAPI-friendly DB dependency that yields a Session and closes it.

    Use this with `Depends(get_db)` in route functions to ensure the session
    lifecycle works with both sync and async endpoints under FastAPI.
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    """
    Create all tables defined in metadata.
    
    This is idempotent - tables that already exist will not be recreated.
    """
    engine = get_engine()
    metadata.create_all(bind=engine)
    apply_schema_upgrades(engine)


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


def apply_schema_upgrades(engine=None) -> None:
    """Apply lightweight, idempotent schema upgrades for Phase 4.2.

    Adds enforcement columns if the plans table already exists without them
    (common in developer databases) and leaves existing data intact.
    """
    eng = engine or get_engine()
    with eng.connect() as conn:
        conn.execute(
            text(
                """
                ALTER TABLE plans
                ADD COLUMN IF NOT EXISTS enforcement_enabled BOOLEAN NOT NULL DEFAULT false;
                """
            )
        )
        conn.execute(
            text(
                """
                ALTER TABLE plans
                ADD COLUMN IF NOT EXISTS enforcement_grace_count INTEGER NOT NULL DEFAULT 0;
                """
            )
        )
        conn.commit()


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

# Users table (Phase 4.0)
users = Table(
    'app_users',
    metadata,
    Column('user_id', String(100), primary_key=True),
    Column('display_name', Text, nullable=True),
    Column('status', String(50), nullable=False, server_default='active'),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Index('idx_users_created_at', 'created_at'),
)

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

# Plans table (Phase 4.1 - Monetization Hooks)
plans = Table(
    'plans',
    metadata,
    Column('plan_id', String(50), primary_key=True),
    Column('name', String(200), nullable=False),
    Column('is_default', Boolean, nullable=False, server_default='false'),
    Column('enforcement_enabled', Boolean, nullable=False, server_default='false'),
    Column('enforcement_grace_count', Integer, nullable=False, server_default='0'),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    # Index for finding default plan
    Index('idx_plans_is_default', 'is_default'),
)

# Plan entitlements table (Phase 4.1)
plan_entitlements = Table(
    'plan_entitlements',
    metadata,
    Column('plan_id', String(50), ForeignKey('plans.plan_id'), nullable=False),
    Column('entitlement_key', String(100), nullable=False),
    Column('value', JSON, nullable=False),
    # Primary key is composite (plan_id, entitlement_key)
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    # Composite primary key
    UniqueConstraint('plan_id', 'entitlement_key', name='uq_plan_entitlements_plan_key'),
    # Index for querying entitlements by plan
    Index('idx_plan_entitlements_plan_id', 'plan_id'),
)

# User plans table (Phase 4.1)
user_plans = Table(
    'user_plans',
    metadata,
    Column('user_id', String(100), ForeignKey('app_users.user_id'), primary_key=True),
    Column('plan_id', String(50), ForeignKey('plans.plan_id'), nullable=False),
    Column('assigned_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    # Index for finding all users on a plan
    Index('idx_user_plans_plan_id', 'plan_id'),
)

# Usage events table (Phase 4.1)
usage_events = Table(
    'usage_events',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', String(100), ForeignKey('app_users.user_id'), nullable=False),
    Column('usage_key', String(100), nullable=False),
    Column('occurred_at', DateTime(timezone=True), nullable=False),
    Column('metadata', JSON, nullable=True),
    # Composite index for usage queries: (user_id, usage_key, occurred_at)
    Index('idx_usage_events_user_key_occurred', 'user_id', 'usage_key', 'occurred_at'),
    # Index for time-range queries
    Index('idx_usage_events_occurred_at', 'occurred_at'),
)

# Entitlement overrides (Phase 4.2)
entitlement_overrides = Table(
    'entitlement_overrides',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', String(100), ForeignKey('app_users.user_id'), nullable=False, index=True),
    Column('entitlement_key', String(100), nullable=False),
    Column('override_value', JSON, nullable=False),
    Column('reason', Text, nullable=True),
    Column('expires_at', DateTime(timezone=True), nullable=True),
    Column('created_by', String(100), nullable=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint('user_id', 'entitlement_key', name='uq_entitlement_overrides_user_key'),
    Index('idx_entitlement_overrides_user', 'user_id'),
)

# Entitlement grace usage (Phase 4.2)
entitlement_grace_usage = Table(
    'entitlement_grace_usage',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', String(100), ForeignKey('app_users.user_id'), nullable=False, index=True),
    Column('plan_id', String(50), ForeignKey('plans.plan_id'), nullable=False),
    Column('entitlement_key', String(100), nullable=False),
    Column('used', Integer, nullable=False, server_default='0'),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    UniqueConstraint('user_id', 'plan_id', 'entitlement_key', name='uq_entitlement_grace_usage'),
    Index('idx_entitlement_grace_usage_user', 'user_id'),
)

# Billing customers (Phase 4.3 - Stripe Integration)
billing_customers = Table(
    'billing_customers',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', String(100), ForeignKey('app_users.user_id'), nullable=False, unique=True, index=True),
    Column('stripe_customer_id', String(100), nullable=False, unique=True, index=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    Index('idx_billing_customers_user_id', 'user_id'),
    Index('idx_billing_customers_stripe_id', 'stripe_customer_id'),
)

# Billing subscriptions (Phase 4.3)
billing_subscriptions = Table(
    'billing_subscriptions',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('user_id', String(100), ForeignKey('app_users.user_id'), nullable=False, index=True),
    Column('stripe_subscription_id', String(100), nullable=False, unique=True, index=True),
    Column('plan_id', String(50), ForeignKey('plans.plan_id'), nullable=False),
    Column('status', String(50), nullable=False, index=True),  # active, canceled, past_due, etc.
    Column('current_period_end', DateTime(timezone=True), nullable=True),
    Column('cancel_at_period_end', Boolean, nullable=False, server_default='false'),
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('updated_at', DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
    Index('idx_billing_subscriptions_user_id', 'user_id'),
    Index('idx_billing_subscriptions_stripe_id', 'stripe_subscription_id'),
    Index('idx_billing_subscriptions_status', 'status'),
)

# Billing events (Phase 4.3 - Webhook idempotency)
billing_events = Table(
    'billing_events',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('stripe_event_id', String(100), nullable=False, unique=True, index=True),
    Column('event_type', String(100), nullable=False, index=True),
    Column('received_at', DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column('payload_hash', String(64), nullable=False),  # SHA256 hash for deduplication
    Column('processed', Boolean, nullable=False, server_default='false', index=True),
    Column('processed_at', DateTime(timezone=True), nullable=True),
    Column('error', Text, nullable=True),
    UniqueConstraint('stripe_event_id', name='uq_billing_events_stripe_id'),
    Index('idx_billing_events_stripe_event_id', 'stripe_event_id'),
    Index('idx_billing_events_received_at', 'received_at'),
    Index('idx_billing_events_processed', 'processed'),
)

# Admin audit log (Phase 4.4)
billing_admin_audit = Table(
    'billing_admin_audit',
    metadata,
    Column('id', Integer, primary_key=True, autoincrement=True),
    Column('actor', String(100), nullable=False),  # "admin_key" or key hash
    Column('action', String(100), nullable=False),  # "replay_webhook", "override_entitlement", etc.
    Column('target_user_id', String(100), nullable=True, index=True),
    Column('target_resource', String(200), nullable=True),  # stripe_event_id, entitlement_key, etc.
    Column('payload_json', Text, nullable=True),  # Full request/decision payload as JSON
    Column('created_at', DateTime(timezone=True), server_default=func.now(), nullable=False, index=True),
    # Indexes for querying audit logs
    Index('idx_billing_admin_audit_actor', 'actor'),
    Index('idx_billing_admin_audit_action', 'action'),
    Index('idx_billing_admin_audit_user_id', 'target_user_id'),
    Index('idx_billing_admin_audit_created_at', 'created_at'),
)

