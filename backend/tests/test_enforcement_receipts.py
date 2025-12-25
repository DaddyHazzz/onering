import pytest
from datetime import datetime, timedelta, timezone

from backend.features.enforcement.contracts import EnforcementReceipt
from backend.features.enforcement.service import EnforcementRequest, run_enforcement_pipeline
from backend.core.config import settings


@pytest.mark.asyncio
async def test_receipt_ttl_respected(monkeypatch):
    fixed = datetime(2025, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr("backend.features.enforcement.service._now", lambda: fixed)
    monkeypatch.setattr("backend.features.enforcement.service.get_enforcement_mode", lambda: "advisory")
    monkeypatch.setattr("backend.features.enforcement.service.write_agent_decisions", lambda *args, **kwargs: True)
    monkeypatch.setattr(settings, "ONERING_ENFORCEMENT_RECEIPT_TTL_SECONDS", 3600)

    result = run_enforcement_pipeline(
        EnforcementRequest(
            prompt="hello",
            platform="x",
            user_id="u",
            request_id="r1",
            content="test content",
        )
    )

    assert result.receipt is not None
    assert result.receipt.expires_at == fixed + timedelta(seconds=3600)


@pytest.mark.asyncio
async def test_validate_receipt_required(client):
    res = await client.post("/v1/enforcement/receipts/validate", json={})
    data = res.json()
    assert data["ok"] is False
    assert data["code"] == "ENFORCEMENT_RECEIPT_REQUIRED"


@pytest.mark.asyncio
async def test_validate_receipt_invalid(client, monkeypatch):
    monkeypatch.setattr("backend.api.enforcement.resolve_receipt", lambda **kwargs: (None, "ENFORCEMENT_RECEIPT_INVALID"))
    res = await client.post("/v1/enforcement/receipts/validate", json={"request_id": "r1"})
    data = res.json()
    assert data["ok"] is False
    assert data["code"] == "ENFORCEMENT_RECEIPT_INVALID"


@pytest.mark.asyncio
async def test_validate_receipt_expired(client, monkeypatch):
    expired = datetime.now(timezone.utc) - timedelta(seconds=10)
    receipt = EnforcementReceipt(
        receipt_id="r1",
        request_id="r1",
        draft_id=None,
        ring_id=None,
        turn_id=None,
        qa_status="PASS",
        qa_decision_hash="h",
        policy_version="10.1",
        created_at=expired - timedelta(seconds=10),
        expires_at=expired,
    )
    monkeypatch.setattr("backend.api.enforcement.resolve_receipt", lambda **kwargs: (receipt, None))
    res = await client.post("/v1/enforcement/receipts/validate", json={"request_id": "r1"})
    data = res.json()
    assert data["ok"] is False
    assert data["code"] == "ENFORCEMENT_RECEIPT_EXPIRED"


@pytest.mark.asyncio
async def test_validate_receipt_pass(client, monkeypatch):
    receipt = EnforcementReceipt(
        receipt_id="r1",
        request_id="r1",
        draft_id=None,
        ring_id=None,
        turn_id=None,
        qa_status="PASS",
        qa_decision_hash="h",
        policy_version="10.1",
        created_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=60),
    )
    monkeypatch.setattr("backend.api.enforcement.resolve_receipt", lambda **kwargs: (receipt, None))
    res = await client.post("/v1/enforcement/receipts/validate", json={"request_id": "r1"})
    data = res.json()
    assert data["ok"] is True
    assert data["receipt"]["qa_status"] == "PASS"
