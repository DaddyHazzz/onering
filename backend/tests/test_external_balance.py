"""
Phase 10.2: External API balance reflects ledger truth in shadow/live.
"""
from datetime import datetime, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.core.database import get_db
from backend.features.tokens import balance as balance_module
from backend.main import app

client = TestClient(app)


def test_external_rings_uses_effective_balance(monkeypatch):
    monkeypatch.setenv("ONERING_EXTERNAL_API_ENABLED", "1")
    monkeypatch.setattr(balance_module, "get_token_issuance_mode", lambda: "shadow")

    db = next(get_db())
    user_id = f"ext_user_{uuid.uuid4()}"
    db.execute(
        text('INSERT INTO users (id, "clerkId", "ringBalance", "createdAt", "updatedAt") VALUES (:id, :clerk_id, 100, NOW(), NOW())'),
        {"id": str(uuid.uuid4()), "clerk_id": user_id},
    )
    db.execute(
        text(
            """
            INSERT INTO ring_pending (user_id, amount, reason_code, metadata, created_at)
            VALUES (:user_id, 50, 'shadow', '{}'::jsonb, :created_at)
            """
        ),
        {"user_id": user_id, "created_at": datetime.now(timezone.utc)},
    )
    db.execute(
        text(
            """
            INSERT INTO ring_ledger (user_id, event_type, reason_code, amount, balance_after, metadata, created_at)
            VALUES (:user_id, 'SPEND', 'shadow_spend', -10, 90, '{}'::jsonb, :created_at)
            """
        ),
        {"user_id": user_id, "created_at": datetime.now(timezone.utc)},
    )
    db.commit()

    db.close()

    monkeypatch.setattr(
        "backend.api.external.validate_api_key",
        lambda _db, _key, client_ip=None: {
            "key_id": "test_key",
            "owner_user_id": user_id,
            "scopes": ["read:rings"],
            "rate_limit_tier": "free",
        },
    )
    monkeypatch.setattr(
        "backend.api.external.check_rate_limit",
        lambda _db, _key_id, _tier: (True, 0, 100, datetime.now(timezone.utc)),
    )

    res = client.get(
        "/v1/external/rings",
        headers={"Authorization": "Bearer test_key"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["rings"][0]["balance"] == 140

    db = next(get_db())
    db.execute(text('DELETE FROM ring_pending WHERE user_id = :user_id'), {"user_id": user_id})
    db.execute(text('DELETE FROM ring_ledger WHERE user_id = :user_id'), {"user_id": user_id})
    db.execute(text('DELETE FROM users WHERE "clerkId" = :user_id'), {"user_id": user_id})
    db.commit()
    db.close()
