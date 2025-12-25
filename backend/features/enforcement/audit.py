"""Audit logging for agent enforcement decisions."""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable

from sqlalchemy import insert

from backend.core.config import settings
from backend.core.database import audit_agent_decisions, create_all_tables, get_db_session

logger = logging.getLogger("onering.enforcement.audit")


def _audit_enabled() -> bool:
    value = getattr(settings, "ONERING_AUDIT_LOG", "0")
    return str(value).strip() == "1"


def write_agent_decision(
    record: Dict[str, Any],
    *,
    mode: str,
) -> bool:
    if not _audit_enabled():
        return True

    try:
        create_all_tables()
        with get_db_session() as session:
            session.execute(insert(audit_agent_decisions).values(**record))
        return True
    except Exception as exc:
        logger.warning("audit write failed: %s", exc)
        return mode != "enforced"


def write_agent_decisions(
    records: Iterable[Dict[str, Any]],
    *,
    mode: str,
) -> bool:
    ok = True
    for record in records:
        if not write_agent_decision(record, mode=mode):
            ok = False
    return ok
