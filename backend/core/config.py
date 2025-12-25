import logging

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Environment
    ENV: str = "development"
    CONFIG_STRICT: bool = False

    # Core APIs
    GROQ_API_KEY: Optional[str] = None

    # Clerk Auth
    CLERK_SECRET_KEY: Optional[str] = None
    NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: Optional[str] = None
    NEXT_PUBLIC_CLERK_SIGN_IN_URL: Optional[str] = None
    NEXT_PUBLIC_CLERK_SIGN_UP_URL: Optional[str] = None
    NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL: Optional[str] = None
    NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL: Optional[str] = None

    # Database & Cache
    DATABASE_URL: Optional[str] = None
    TEST_DATABASE_URL: Optional[str] = None
    REDIS_URL: str = "redis://localhost:6379"

    # X/Twitter API
    TWITTER_API_KEY: Optional[str] = None
    TWITTER_API_SECRET: Optional[str] = None
    TWITTER_ACCESS_TOKEN: Optional[str] = None
    TWITTER_ACCESS_TOKEN_SECRET: Optional[str] = None
    X_OATH2_CLIENT_ID: Optional[str] = None
    X_OATH2_CLIENT_SECRET: Optional[str] = None

    # Stripe
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID: Optional[str] = None
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: Optional[str] = None

    # App URLs
    BACKEND_URL: str = "http://localhost:8000"
    BASE_URL: str = "http://localhost:8000"

    # Rate limiting (Phase 6.3)
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_PER_MINUTE_DEFAULT: int = 120
    RATE_LIMIT_BURST_DEFAULT: int = 30

    # Observability / Tracing (Phase 7)
    OTEL_ENABLED: bool = False
    OTEL_EXPORTER: str = "console"  # console | memory

    # WebSocket limits (Phase 6.3)
    WS_LIMITS_ENABLED: bool = False
    WS_MAX_SOCKETS_PER_USER: int = 3
    WS_MAX_SOCKETS_PER_DRAFT: int = 100
    WS_MAX_SOCKETS_GLOBAL: int = 1000
    WS_MAX_MESSAGE_BYTES: int = 4096
    WS_ALLOWED_ORIGINS: str = "*"  # comma-separated

    # Scale safety caps (Phase 7)
    MAX_WS_CONNECTIONS_PER_DRAFT: int = 0  # 0 = disabled
    MAX_COLLABORATORS_PER_DRAFT: int = 0  # 0 = disabled
    MAX_SEGMENTS_PER_DRAFT: int = 0  # 0 = disabled (soft cap: warn only)

    # Audit logging (Phase 6.3)
    AUDIT_ENABLED: bool = False
    AUDIT_SAMPLE_RATE: float = 1.0

    # Admin access (Phase 4.6: hybrid auth)
    ADMIN_KEY: Optional[str] = None  # Legacy key (backward compatible)
    ADMIN_AUTH_MODE: str = "hybrid"  # "clerk" | "legacy" | "hybrid"
    ENVIRONMENT: str = "dev"  # "dev" | "test" | "prod"
    
    # Clerk JWT verification
    CLERK_ISSUER: Optional[str] = None  # e.g. https://your-instance.clerk.accounts.dev
    CLERK_AUDIENCE: Optional[str] = None  # typically the app domain or API identifier
    CLERK_JWKS_URL: Optional[str] = None  # e.g. https://your-instance.clerk.accounts.dev/.well-known/jwks.json

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
settings = Settings()


def validate_config(strict: Optional[bool] = None, settings_obj: Optional[Settings] = None, logger: Optional[logging.Logger] = None) -> bool:
    """Validate required configuration.

    In strict mode raise RuntimeError; otherwise emit warnings only.
    Secrets are not logged, only missing keys.
    """
    cfg = settings_obj or settings
    log = logger or logging.getLogger("onering")
    strict_mode = strict if strict is not None else getattr(cfg, "CONFIG_STRICT", False)

    required_keys = [
        "DATABASE_URL",
        "CLERK_SECRET_KEY",
        "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY",
        "GROQ_API_KEY",
        "STRIPE_SECRET_KEY",
    ]

    missing = [key for key in required_keys if not getattr(cfg, key, None)]
    if missing:
        message = f"Missing required configuration: {', '.join(missing)}"
        if strict_mode:
            raise RuntimeError(message)
        log.warning(message)

    return True
