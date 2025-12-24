from sqlalchemy import select

from backend.features.audit.service import record_audit_event, get_buffered_audit_events
from backend.core.database import audit_events, create_all_tables, get_engine
from backend.core.config import settings


def test_audit_logging_inserts_row(monkeypatch):
    monkeypatch.setattr(settings, "AUDIT_ENABLED", True)
    monkeypatch.setattr(settings, "AUDIT_SAMPLE_RATE", 1.0)
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite:///:memory:")

    create_all_tables()

    record_audit_event(
        action="collab.test",
        user_id="user-123",
        draft_id="draft-123",
        request_id="rid-123",
        metadata={"foo": "bar"},
        ip="127.0.0.1",
        user_agent="pytest",
    )

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(select(audit_events)).fetchall()
    assert len(rows) == 1
    row = rows[0]
    assert row.request_id == "rid-123"
    assert row.user_id == "user-123"
    assert row.action == "collab.test"
    assert row.draft_id == "draft-123"


def test_audit_buffer_when_no_db(monkeypatch):
    monkeypatch.setattr(settings, "AUDIT_ENABLED", True)
    monkeypatch.setattr(settings, "AUDIT_SAMPLE_RATE", 1.0)
    monkeypatch.setattr(settings, "DATABASE_URL", None)
    # Ensure no DB URL set
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    before = len(get_buffered_audit_events())
    record_audit_event(action="collab.test", user_id="u1")
    after = len(get_buffered_audit_events())

    assert after == before + 1
