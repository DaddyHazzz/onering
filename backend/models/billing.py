"""
Billing models for OneRing.
Includes subscriptions, events, grace periods, and admin audit trails.
"""

from datetime import datetime, timezone
import json
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey, JSON, Index
from sqlalchemy import Text
from sqlalchemy.orm import relationship, synonym, declarative_base
import uuid

Base = declarative_base()


def utc_now():
    """Timezone-aware UTC now for SQLAlchemy defaults."""
    return datetime.now(timezone.utc)


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
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
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
    created_at = Column(DateTime, default=utc_now, index=True)
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
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    
    # Relations
    subscription = relationship("BillingSubscription", back_populates="grace_periods")
    
    __table_args__ = (
        Index("ix_billing_grace_periods_subscription_id", "subscription_id"),
    )


class BillingAdminAudit(Base):
    """Admin audit trail for billing operations (Phase 4.6.1 schema)."""
    __tablename__ = "billing_admin_audit"

    # Align with core.database.billing_admin_audit definition
    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String(100), nullable=False, index=True)  # Legacy display/identifier
    actor_id = Column(String(255), nullable=True, index=True)
    actor_type = Column(String(20), nullable=True)
    actor_email = Column(String(255), nullable=True)
    auth_mechanism = Column(String(20), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    target_user_id = Column(String(100), nullable=True, index=True)
    target_resource = Column(String(200), nullable=True)
    payload_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, index=True)

    # Backward compatibility: tests and legacy code still expect user_id
    user_id = synonym("target_user_id")

    @property
    def _payload(self) -> Dict[str, Any]:
        try:
            if isinstance(self.payload_json, str):
                return json.loads(self.payload_json)
            return self.payload_json or {}
        except Exception:
            return {}

    @property
    def target_credits(self) -> Optional[int]:
        return self._payload.get("credits")

    @property
    def target_plan(self) -> Optional[str]:
        return self._payload.get("plan")

    __table_args__ = (
        Index("idx_billing_admin_audit_actor", "actor"),
        Index("idx_billing_admin_audit_actor_id", "actor_id"),
        Index("idx_billing_admin_audit_action", "action"),
        Index("idx_billing_admin_audit_user_id", "target_user_id"),
        Index("idx_billing_admin_audit_created_at", "created_at"),
    )
