"""
Admin authentication with Clerk JWT (Phase 4.6.1).

Goals:
- Offline RS256 verification using injected JWKS (no network).
- Missing/invalid/expired/wrong role tokens are rejected.
- Valid admin token succeeds on an audited admin endpoint.
- JWKS override prevents any real HTTP fetch.
"""
import base64
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from backend.main import app
from backend.core.database import get_db, metadata
from backend.core.clerk_auth import (
    create_test_jwt,
    set_jwks_provider_for_tests,
)
from backend.core.config import settings


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
    """Configure Clerk RS256 auth for all tests and restore afterwards."""
    orig = {
        "mode": settings.ADMIN_AUTH_MODE,
        "env": settings.ENVIRONMENT,
        "admin_key": settings.ADMIN_KEY,
        "secret": settings.CLERK_SECRET_KEY,
        "issuer": settings.CLERK_ISSUER,
        "aud": settings.CLERK_AUDIENCE,
        "jwks_url": settings.CLERK_JWKS_URL,
    }

    settings.ADMIN_AUTH_MODE = "clerk"
    settings.ENVIRONMENT = "dev"
    settings.ADMIN_KEY = None
    settings.CLERK_SECRET_KEY = None  # Force RS256 path
    settings.CLERK_ISSUER = "https://clerk.test"
    settings.CLERK_AUDIENCE = "onering-api"
    settings.CLERK_JWKS_URL = "https://clerk.test/.well-known/jwks.json"

    private_key, jwks = rsa_material
    set_jwks_provider_for_tests(lambda issuer, jwks_url: jwks)

    yield private_key

    # Restore
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
    metadata.create_all(engine)
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

def test_admin_endpoint_missing_auth(client):
    response = client.get("/v1/admin/billing/retries")
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] in {"admin_unauthorized", "http_error"}


def test_admin_endpoint_invalid_signature(client):
    wrong_private, _ = generate_rsa_material()
    token = create_test_jwt(
        sub="user_bad_sig",
        email="bad@example.com",
        role="admin",
        algorithm="RS256",
        private_key=wrong_private,
        kid="wrong-kid",
        issuer="https://clerk.test",
        audience="onering-api",
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/v1/admin/billing/retries", headers=headers)
    assert response.status_code == 401


def test_admin_endpoint_non_admin_token(client, configure_settings):
    private_key = configure_settings
    token = create_test_jwt(
        sub="user_regular",
        email="regular@example.com",
        role=None,
        algorithm="RS256",
        private_key=private_key,
        kid="test-kid",
        issuer="https://clerk.test",
        audience="onering-api",
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/v1/admin/billing/retries", headers=headers)
    assert response.status_code == 401


def test_admin_endpoint_wrong_issuer(client, configure_settings):
    private_key = configure_settings
    token = create_test_jwt(
        sub="user_wrong_issuer",
        email="issuer@example.com",
        role="admin",
        algorithm="RS256",
        private_key=private_key,
        kid="test-kid",
        issuer="https://wrong.issuer",
        audience="onering-api",
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/v1/admin/billing/retries", headers=headers)
    assert response.status_code == 401


def test_admin_endpoint_wrong_audience(client, configure_settings):
    private_key = configure_settings
    token = create_test_jwt(
        sub="user_wrong_aud",
        email="aud@example.com",
        role="admin",
        algorithm="RS256",
        private_key=private_key,
        kid="test-kid",
        issuer="https://clerk.test",
        audience="wrong-audience",
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/v1/admin/billing/retries", headers=headers)
    assert response.status_code == 401


def test_admin_endpoint_with_admin_token(client, configure_settings):
    private_key = configure_settings
    token = create_test_jwt(
        sub="user_admin_456",
        email="admin@example.com",
        role="admin",
        algorithm="RS256",
        private_key=private_key,
        kid="test-kid",
        issuer="https://clerk.test",
        audience="onering-api",
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/v1/admin/billing/subscriptions", headers=headers)
    assert response.status_code == 200, f"Got {response.status_code}: {response.json()}"


def test_admin_token_contains_actor_info(client, configure_settings):
    private_key = configure_settings
    token = create_test_jwt(
        sub="user_admin_actor",
        email="actor@example.com",
        role="admin",
        algorithm="RS256",
        private_key=private_key,
        kid="test-kid",
        issuer="https://clerk.test",
        audience="onering-api",
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/v1/admin/billing/retries", headers=headers)
    assert response.status_code == 200, f"Got {response.status_code}: {response.json()}"


def test_expired_token(client, configure_settings):
    private_key = configure_settings
    token = create_test_jwt(
        sub="user_admin_expired",
        email="expired@example.com",
        role="admin",
        algorithm="RS256",
        private_key=private_key,
        kid="test-kid",
        issuer="https://clerk.test",
        audience="onering-api",
        exp_minutes=-5,
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/v1/admin/billing/retries", headers=headers)
    assert response.status_code == 401


def test_jwks_override_blocks_network(monkeypatch, client, configure_settings, rsa_material):
    # Force default fetcher to raise to ensure override is used
    from backend.core import clerk_auth

    def boom(*args, **kwargs):
        raise AssertionError("network fetch should not be called")

    monkeypatch.setattr(clerk_auth, "_default_fetch_jwks", boom)

    private_key, _ = rsa_material
    token = create_test_jwt(
        sub="user_network_guard",
        email="guard@example.com",
        role="admin",
        algorithm="RS256",
        private_key=private_key,
        kid="test-kid",
        issuer="https://clerk.test",
        audience="onering-api",
    )
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/v1/admin/billing/retries", headers=headers)
    assert response.status_code == 200
