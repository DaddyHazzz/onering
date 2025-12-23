"""
Billing models for OneRing.
Includes subscriptions, events, grace periods, and admin audit trails.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()


class BillingSubscription(Base):
    """User billing subscription state."""
    __tablename__ = "billing_subscriptions"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), ForeignKey("user.id"), nullable=False, unique=True, index=True)
    
    # Stripe details
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, unique=True, index=True)
    
    # Entitlements
    plan = Column(String(50), default="starter")  # starter, pro, enterprise
    credits = Column(Integer, default=0)
    valid_until = Column(DateTime, nullable=True)
    
    # Status tracking
    status = Column(String(50), default="active")  # active, past_due, canceled, unpaid
    is_on_grace_period = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    events = relationship("BillingEvent", back_populates="subscription")
    grace_periods = relationship("BillingGracePeriod", back_populates="subscription")
    
    __table_args__ = (
        Index("ix_billing_subscriptions_user_id_status", "user_id", "status"),
    )


class BillingEvent(Base):
    """Billing event log (webhooks, plan changes, etc.)."""
    __tablename__ = "billing_events"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(255), ForeignKey("user.id"), nullable=False, index=True)
    subscription_id = Column(String(36), ForeignKey("billing_subscriptions.id"), nullable=True)
    
    # Event metadata
    event_type = Column(String(100), nullable=False, index=True)  # checkout.session.completed, customer.subscription.updated, etc.
    stripe_event_id = Column(String(255), unique=True, nullable=True, index=True)
    
    # Processing status
    status = Column(String(50), default="pending")  # pending, processed, failed
    error_message = Column(String(500), nullable=True)
    
    # Event payload
    event_data = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime, nullable=True)
    
    # Relations
    subscription = relationship("BillingSubscription", back_populates="events")
    
    __table_args__ = (
        Index("ix_billing_events_user_id_status", "user_id", "status"),
        Index("ix_billing_events_event_type_status", "event_type", "status"),
    )


class BillingGracePeriod(Base):
    """Grace period for failed payments."""
    __tablename__ = "billing_grace_periods"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id = Column(String(36), ForeignKey("billing_subscriptions.id"), nullable=False, unique=True)
    
    # Grace period dates
    grace_until = Column(DateTime, nullable=False)
    reason = Column(String(255), nullable=True)  # payment_failed, manual_override, etc.
    
    # Audit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    subscription = relationship("BillingSubscription", back_populates="grace_periods")
    
    __table_args__ = (
        Index("ix_billing_grace_periods_subscription_id", "subscription_id"),
    )


class BillingAdminAudit(Base):
    """Admin audit trail for billing operations."""
    __tablename__ = "billing_admin_audit"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Action
    action = Column(String(100), nullable=False, index=True)  # entitlement_override, grace_period_reset, webhook_replay, etc.
    
    # Actors
    user_id = Column(String(255), ForeignKey("user.id"), nullable=False, index=True)
    admin_id = Column(String(255), nullable=False, index=True)  # Future: Link to admin user
    
    # Changes
    target_credits = Column(Integer, nullable=True)
    target_plan = Column(String(50), nullable=True)
    target_valid_until = Column(DateTime, nullable=True)
    target_grace_until = Column(DateTime, nullable=True)
    
    # Details and reason
    details = Column(JSON, nullable=True)
    reason = Column(String(500), nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relations
    
    __table_args__ = (
        Index("ix_billing_admin_audit_user_id_action", "user_id", "action"),
        Index("ix_billing_admin_audit_admin_id", "admin_id"),
    )
