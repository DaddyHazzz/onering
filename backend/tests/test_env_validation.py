"""Tests for environment validation (Phase 3.8)."""

import os
from types import SimpleNamespace

import pytest

from backend.core.validation import validate_env, EnvValidationError


def make_settings(**overrides):
    defaults = dict(
        ENV="development",
        DATABASE_URL=None,
        TEST_DATABASE_URL=None,
        CLERK_SECRET_KEY=None,
        GROQ_API_KEY=None,
        STRIPE_SECRET_KEY=None,
        TWITTER_ACCESS_TOKEN=None,
        TWITTER_ACCESS_TOKEN_SECRET=None,
        X_OATH2_CLIENT_ID=None,
        X_OATH2_CLIENT_SECRET=None,
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_valid_production_config_passes(monkeypatch):
    settings = make_settings(
        ENV="production",
        DATABASE_URL="postgresql://user:pass@localhost:5432/onering",
        CLERK_SECRET_KEY="sk_test",
        GROQ_API_KEY="gsk_test",
        STRIPE_SECRET_KEY="sk_stripe",
    )
    validate_env(settings_obj=settings)


def test_missing_database_url_in_production_fails():
    settings = make_settings(
        ENV="production",
        CLERK_SECRET_KEY="sk_test",
        GROQ_API_KEY="gsk_test",
        STRIPE_SECRET_KEY="sk_stripe",
    )
    with pytest.raises(EnvValidationError):
        validate_env(settings_obj=settings)


def test_invalid_database_url_format_fails():
    settings = make_settings(
        ENV="production",
        DATABASE_URL="not-a-url",
        CLERK_SECRET_KEY="sk_test",
        GROQ_API_KEY="gsk_test",
        STRIPE_SECRET_KEY="sk_stripe",
    )
    with pytest.raises(EnvValidationError):
        validate_env(settings_obj=settings)


def test_test_database_url_forbidden_in_prod():
    settings = make_settings(
        ENV="production",
        DATABASE_URL="postgresql://user:pass@localhost:5432/onering",
        CLERK_SECRET_KEY="sk_test",
        GROQ_API_KEY="gsk_test",
        STRIPE_SECRET_KEY="sk_stripe",
        TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/onering_test",
    )
    with pytest.raises(EnvValidationError):
        validate_env(settings_obj=settings)


def test_mutually_exclusive_vars_raise():
    settings = make_settings(
        ENV="production",
        DATABASE_URL="postgresql://user:pass@localhost:5432/onering",
        CLERK_SECRET_KEY="sk_test",
        GROQ_API_KEY="gsk_test",
        STRIPE_SECRET_KEY="sk_stripe",
        TWITTER_ACCESS_TOKEN="token",
        X_OATH2_CLIENT_ID="oauth-client",
    )
    with pytest.raises(EnvValidationError):
        validate_env(settings_obj=settings)


def test_skip_env_validation_bypass(monkeypatch):
    monkeypatch.setenv("SKIP_ENV_VALIDATION", "1")
    settings = make_settings(ENV="production")
    validate_env(settings_obj=settings)
    monkeypatch.delenv("SKIP_ENV_VALIDATION", raising=False)


def test_test_database_url_only_allowed_in_test_mode():
    settings = make_settings(
        ENV="development",
        TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/onering_test",
    )
    with pytest.raises(EnvValidationError):
        validate_env(settings_obj=settings)
