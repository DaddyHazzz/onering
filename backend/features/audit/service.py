import random
import logging
from typing import Any, Dict, Optional
from datetime import datetime, timezone

from sqlalchemy import insert

from backend.core.config import settings
from backend.core.database import audit_events, get_db_session, create_all_tables, get_database_url

logger = logging.getLogger(__name__)

_memory_events = []  # Fallback buffer when DB is unavailable


def _safe_truncate(value: Any, limit: int = 500):
    try:
        text = str(value)
    except Exception:
        return "<unserializable>"
    if len(text) <= limit:
        return text
    return text[:limit] + "...<truncated>"


def _should_sample() -> bool:
    rate = settings.AUDIT_SAMPLE_RATE if settings.AUDIT_SAMPLE_RATE is not None else 1.0
    try:
        rate_val = float(rate)
    except Exception:
        rate_val = 1.0
    if rate_val >= 1.0:
        return True
    if rate_val <= 0:
        return False
    return random.random() <= rate_val


def record_audit_event(
    *,
    action: str,
    user_id: Optional[str],
    draft_id: Optional[str] = None,
    request_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    ip: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Record an audit event to the database (or fallback buffer).

    Notes:
    - Respects AUDIT_ENABLED and AUDIT_SAMPLE_RATE.
    - Never logs secrets; metadata is truncated.
    """

    if not settings.AUDIT_ENABLED:
        return

    if not _should_sample():
        return

    safe_metadata = None
    if metadata:
        safe_metadata = {k: _safe_truncate(v) for k, v in metadata.items()}

    record = {
        "ts": datetime.now(timezone.utc),
        "request_id": request_id,
        "user_id": user_id,
        "action": action,
        "draft_id": draft_id,
        "metadata": safe_metadata,
        "ip": ip,
        "user_agent": _safe_truncate(user_agent) if user_agent else None,
    }

    db_url = get_database_url()
    if not db_url:
        _memory_events.append(record)
        logger.debug("Audit event buffered in memory (no DB configured)")
        return

    try:
        create_all_tables()
        with get_db_session() as session:
            session.execute(insert(audit_events).values(**record))
    except Exception as exc:
        logger.warning(f"Audit event write failed: {exc}")
        _memory_events.append(record)


def get_buffered_audit_events():
    return list(_memory_events)
