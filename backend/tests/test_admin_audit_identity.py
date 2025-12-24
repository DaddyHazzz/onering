"""
Admin audit identity tests (Phase 4.6.1).

Verifies that admin actions record actor identity for both Clerk JWT and legacy key paths.
Uses offline RS256 tokens with injected JWKS (no network) and in-memory SQLite.
"""
import base64
import pytest
from sqlalchemy import create_engine, select, Table, Column, String
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from fastapi.testclient import TestClient

from backend.main import app
from backend.core.database import get_db
from backend.core.clerk_auth import create_test_jwt, set_jwks_provider_for_tests
from backend.core.config import settings
from backend.models.billing import (
    BillingSubscription,
    BillingEvent,
    BillingGracePeriod,
    BillingAdminAudit,
    Base as BillingBase,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _b64url_int(val: int) -> str:
    return base64.urlsafe_b64encode(val.to_bytes((val.bit_length() + 7) // 8, "big")).rstrip(b"=").decode("ascii")


def generate_rsa_material():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    pub_numbers = key.public_key().public_numbers()
    jwks = {
        "keys": [
            {
                "kid": "test-kid",
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "n": _b64url_int(pub_numbers.n),
                "e": _b64url_int(pub_numbers.e),
            }
        ]
    }
    return private_pem, jwks


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def rsa_material():
    return generate_rsa_material()


@pytest.fixture(autouse=True)
def configure_settings(rsa_material):
    orig = {
        "mode": settings.ADMIN_AUTH_MODE,
        "env": settings.ENVIRONMENT,
        "admin_key": settings.ADMIN_KEY,
        "secret": settings.CLERK_SECRET_KEY,
        "issuer": settings.CLERK_ISSUER,
        "aud": settings.CLERK_AUDIENCE,
        "jwks_url": settings.CLERK_JWKS_URL,
    }

    settings.ADMIN_AUTH_MODE = "hybrid"
    settings.ENVIRONMENT = "dev"
    settings.ADMIN_KEY = "test-admin-key-audit"
    settings.CLERK_SECRET_KEY = None
    settings.CLERK_ISSUER = "https://clerk.test"
    settings.CLERK_AUDIENCE = "onering-api"
    settings.CLERK_JWKS_URL = "https://clerk.test/.well-known/jwks.json"

    _, jwks = rsa_material
    set_jwks_provider_for_tests(lambda issuer, jwks_url: jwks)

    yield rsa_material[0]

    set_jwks_provider_for_tests(None)
    settings.ADMIN_AUTH_MODE = orig["mode"]
    settings.ENVIRONMENT = orig["env"]
    settings.ADMIN_KEY = orig["admin_key"]
    settings.CLERK_SECRET_KEY = orig["secret"]
    settings.CLERK_ISSUER = orig["issuer"]
    settings.CLERK_AUDIENCE = orig["aud"]
    settings.CLERK_JWKS_URL = orig["jwks_url"]


@pytest.fixture
def test_db():
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    # Stub user table for FK
    user_stub = Table("user", BillingBase.metadata, Column("id", String, primary_key=True), extend_existing=True)
    user_stub.create(bind=engine, checkfirst=True)
    try:
        BillingAdminAudit.__table__.indexes.clear()
    except Exception:
        pass
    for model in [BillingSubscription, BillingEvent, BillingGracePeriod, BillingAdminAudit]:
        model.__table__.create(bind=engine, checkfirst=True)

    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield engine
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):
    return TestClient(app)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _fetch_audits(engine):
    with engine.connect() as conn:
        return conn.execute(select(BillingAdminAudit.__table__)).mappings().all()


def test_clerk_admin_action_records_actor(client, configure_settings, test_db):
    private_key = configure_settings
    token = create_test_jwt(
        sub="user_audit_clerk_123",
        email="audit_clerk@example.com",
        role="admin",
        algorithm="RS256",
        private_key=private_key,
        kid="test-kid",
        issuer="https://clerk.test",
        audience="onering-api",
    )
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post(
        "/v1/admin/billing/entitlements/override",
        headers=headers,
        json={"user_id": "user-123", "credits": 100, "plan": "pro"},
    )
    assert response.status_code == 200, response.json()

    rows = _fetch_audits(test_db)
    assert len(rows) == 1
    row = rows[0]
    assert row["actor_type"] == "clerk"
    assert row["auth_mechanism"] == "clerk_jwt"
    assert row["actor_id"] == "user_audit_clerk_123"
    assert row["target_user_id"] == "user-123"
    assert row["action"] == "entitlement_override"


def test_legacy_admin_action_records_actor(client, test_db):
    headers = {"X-Admin-Key": settings.ADMIN_KEY}

    response = client.post(
        "/v1/admin/billing/entitlements/override",
        headers=headers,
        json={"user_id": "user-legacy", "credits": 50, "plan": "starter"},
    )
    assert response.status_code == 200, response.json()

    rows = _fetch_audits(test_db)
    assert len(rows) == 1
    row = rows[0]
    assert row["actor_type"] == "legacy_key"
    assert row["auth_mechanism"] == "x_admin_key"
    assert row["actor_id"].startswith("legacy:")
    assert row["target_user_id"] == "user-legacy"
    assert row["action"] == "entitlement_override"


def test_audit_log_structure_columns():
    column_names = {col.name for col in BillingAdminAudit.__table__.columns}
    assert "actor" in column_names
    assert "actor_id" in column_names
    assert "actor_type" in column_names
    assert "actor_email" in column_names
    assert "auth_mechanism" in column_names
    assert "action" in column_names
    assert "target_user_id" in column_names
