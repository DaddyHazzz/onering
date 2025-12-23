from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional

class Settings(BaseSettings):
    # Environment
    ENV: str = "development"

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
