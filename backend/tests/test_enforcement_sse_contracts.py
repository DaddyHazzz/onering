import json
import re

import pytest
from httpx import ASGITransport, AsyncClient

from backend.main import app


@pytest.mark.asyncio
async def test_enforcement_sse_payload_contract(monkeypatch):
    import backend.agents.viral_thread as vt

    monkeypatch.setattr(vt, "generate_viral_thread", lambda prompt, user_id=None: ["hello world"])
    monkeypatch.setattr("backend.main.generate_viral_thread", lambda prompt, user_id=None: ["hello world"])
    monkeypatch.setattr("backend.main.get_enforcement_mode", lambda: "advisory")
    monkeypatch.setattr("backend.features.enforcement.service.get_enforcement_mode", lambda: "advisory")
    monkeypatch.setattr("backend.features.enforcement.service.write_agent_decisions", lambda *args, **kwargs: True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        res = await ac.post(
            "/v1/generate/content",
            json={
                "type": "viral_thread",
                "prompt": "topic",
                "platform": "x",
                "user_id": "u",
                "stream": True,
            },
        )
        assert res.status_code == 200
        body = (await res.aread()).decode("utf-8")

    match = re.search(r"event: enforcement\ndata: (.+?)\n\n", body, re.DOTALL)
    assert match, "enforcement event missing"
    payload = json.loads(match.group(1))

    for key in ["request_id", "mode", "receipt", "decisions", "qa_summary", "would_block", "required_edits", "audit_ok"]:
        assert key in payload
    for decision in payload["decisions"]:
        assert decision["status"] in {"PASS", "FAIL"}
    assert payload["qa_summary"]["status"] in {"PASS", "FAIL"}
    assert "receipt_id" in payload["receipt"]
    assert "expires_at" in payload["receipt"]

    snapshot = {
        "mode": payload["mode"],
        "receipt_keys": sorted(payload["receipt"].keys()),
        "qa_summary_keys": sorted(payload["qa_summary"].keys()),
        "decision_keys": sorted(payload["decisions"][0].keys()) if payload["decisions"] else [],
    }
    assert snapshot == {
        "mode": "advisory",
        "receipt_keys": [
            "created_at",
            "draft_id",
            "expires_at",
            "policy_version",
            "qa_decision_hash",
            "qa_status",
            "receipt_id",
            "request_id",
            "ring_id",
            "turn_id",
        ],
        "qa_summary_keys": ["required_edits", "risk_score", "status", "violation_codes"],
        "decision_keys": ["agent_name", "decision_id", "required_edits", "status", "violation_codes"],
    }
