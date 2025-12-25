from datetime import datetime, timedelta, timezone

from sqlalchemy import insert, select, func, delete

from backend.core.database import audit_agent_decisions, create_all_tables, get_db_session
from backend.workers.cleanup_enforcement import cleanup_enforcement_audit


def _insert_decision(created_at):
    return {
        "request_id": "req",
        "draft_id": None,
        "ring_id": None,
        "turn_id": None,
        "user_id": "u",
        "agent_name": "qa_gatekeeper",
        "agent_version": "v1",
        "contract_version": "10.1",
        "policy_version": "10.1",
        "input_hash": "h1",
        "output_hash": "h2",
        "prompt_hash": "h3",
        "decision_json": {"output": {"qa": {"status": "PASS"}, "receipt": {"receipt_id": "r"}}},
        "status": "PASS",
        "created_at": created_at,
    }


def test_cleanup_enforcement_audit():
    create_all_tables()
    now = datetime.now(timezone.utc)
    old = now - timedelta(days=40)
    recent = now - timedelta(days=1)

    with get_db_session() as session:
        session.execute(delete(audit_agent_decisions))
        session.execute(insert(audit_agent_decisions).values(**_insert_decision(old)))
        session.execute(insert(audit_agent_decisions).values(**_insert_decision(recent)))

    dry = cleanup_enforcement_audit(retention_days=30, dry_run=True)
    assert dry["candidates"] == 1
    assert dry["deleted"] == 0

    result = cleanup_enforcement_audit(retention_days=30, dry_run=False)
    assert result["deleted"] == 1

    with get_db_session() as session:
        count = session.execute(select(func.count()).select_from(audit_agent_decisions)).scalar()
    assert count == 1
