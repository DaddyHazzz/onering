"""
Test billing when disabled (Phase 4.3).

Verifies graceful degradation when STRIPE_SECRET_KEY not configured.
"""
import pytest
from backend.features.billing.service import (
    billing_enabled,
    get_provider,
    ensure_customer_for_user,
    start_checkout,
    start_portal,
    get_billing_status,
)


def test_billing_disabled_when_no_stripe_key(monkeypatch):
    """Billing should be disabled when STRIPE_SECRET_KEY not set."""
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    assert billing_enabled() is False


def test_get_provider_returns_none_when_disabled(monkeypatch):
    """get_provider should return None when billing disabled."""
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    assert get_provider() is None


def test_ensure_customer_returns_none_when_disabled(monkeypatch):
    """ensure_customer_for_user should return None when billing disabled."""
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    result = ensure_customer_for_user("user123")
    assert result is None


def test_start_checkout_returns_none_when_disabled(monkeypatch):
    """start_checkout should return None when billing disabled."""
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    result = start_checkout(
        user_id="user123",
        plan_id="creator",
        success_url="http://example.com/success",
        cancel_url="http://example.com/cancel",
    )
    assert result is None


def test_start_portal_returns_none_when_disabled(monkeypatch):
    """start_portal should return None when billing disabled."""
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    result = start_portal(user_id="user123", return_url="http://example.com")
    assert result is None


def test_get_billing_status_when_disabled(monkeypatch):
    """get_billing_status should return enabled=false when billing disabled."""
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    status = get_billing_status("user123")
    
    assert status["enabled"] is False
    assert status["plan_id"] is None
    assert status["status"] is None
    assert status["period_end"] is None
    assert status["cancel_at_period_end"] is False
