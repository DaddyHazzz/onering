"""
Environment validation utilities (Phase 3.8).

Ensures the backend fails fast on misconfiguration while
remaining bypassable for tests via SKIP_ENV_VALIDATION.
"""

import os
import re
from typing import Optional, Iterable
from urllib.parse import urlparse

from backend.core.config import settings


class EnvValidationError(RuntimeError):
    """Raised when environment validation fails."""


def _is_valid_db_url(url: str) -> bool:
    """Basic DATABASE_URL validation using urlparse."""
    parsed = urlparse(url)
    return bool(parsed.scheme and parsed.netloc)


def _require(vars_required: Iterable[str], source: object) -> None:
    for var in vars_required:
        if not getattr(source, var, None):
            raise EnvValidationError(f"{var} is required in production")


def validate_env(env: Optional[str] = None, settings_obj=None) -> bool:
    """Validate environment configuration.

    Args:
        env: Override environment name (defaults to settings.ENV)
        settings_obj: Override settings object (defaults to backend.core.config.settings)

    Returns:
        True if validation passes.

    Raises:
        EnvValidationError when a rule is violated.
    """
    if os.getenv("SKIP_ENV_VALIDATION") == "1":
        return True

    cfg = settings_obj or settings
    mode = (env or getattr(cfg, "ENV", "development") or "development").lower()
    db_url = getattr(cfg, "DATABASE_URL", None)
    test_db_url = getattr(cfg, "TEST_DATABASE_URL", None)

    # Validate DATABASE_URL format if provided
    if db_url and not _is_valid_db_url(db_url):
        raise EnvValidationError("DATABASE_URL must be a valid URL (e.g. postgresql://user:pass@host:port/db)")

    # Required vars in production
    required_prod = [
        "DATABASE_URL",
        "CLERK_SECRET_KEY",
        "GROQ_API_KEY",
        "STRIPE_SECRET_KEY",
    ]

    if mode == "production":
        _require(required_prod, cfg)
        if test_db_url:
            raise EnvValidationError("TEST_DATABASE_URL must not be set in production")
    else:
        # Prevent accidental use of test database outside test mode
        if mode != "test" and test_db_url:
            raise EnvValidationError("TEST_DATABASE_URL is only allowed in test mode")

    if mode == "production":
        # Mutually exclusive variables (choose one auth strategy)
        exclusive_pairs = [
            ("TWITTER_ACCESS_TOKEN", "X_OATH2_CLIENT_ID"),
            ("TWITTER_ACCESS_TOKEN_SECRET", "X_OATH2_CLIENT_SECRET"),
        ]
        for a, b in exclusive_pairs:
            if getattr(cfg, a, None) and getattr(cfg, b, None):
                raise EnvValidationError(f"{a} and {b} cannot both be set; choose one auth strategy")

    return True
