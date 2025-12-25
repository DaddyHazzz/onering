"""Audit logging for agent enforcement decisions."""
from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, Optional

from sqlalchemy import insert, select, text

from backend.core.config import settings
from backend.core.database import audit_agent_decisions, get_db_session
from backend.features.enforcement.contracts import EnforcementReceipt, QA_AGENT_NAME

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


def _get_receipt_by_request_id(request_id: str) -> Optional[EnforcementReceipt]:
    # Option 1: derive enforcement receipts from QA records in audit_agent_decisions.
    if not request_id:
        return None
    with get_db_session() as session:
        stmt = (
            select(audit_agent_decisions.c.decision_json)
            .where(
                audit_agent_decisions.c.request_id == request_id,
                audit_agent_decisions.c.agent_name == QA_AGENT_NAME,
            )
            .order_by(audit_agent_decisions.c.created_at.desc())
            .limit(1)
        )
        row = session.execute(stmt).fetchone()
        if not row:
            return None
        decision_json = row[0] or {}
        receipt_payload = decision_json.get("receipt") if isinstance(decision_json, dict) else None
        if not receipt_payload:
            return None
        return EnforcementReceipt.model_validate(receipt_payload)


def _get_receipt_by_receipt_id(receipt_id: str) -> Optional[EnforcementReceipt]:
    if not receipt_id:
        return None
    with get_db_session() as session:
        stmt = text(
            """
            SELECT decision_json
            FROM audit_agent_decisions
            WHERE agent_name = :agent_name
              AND decision_json->'receipt'->>'receipt_id' = :receipt_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        )
        row = session.execute(
            stmt,
            {"agent_name": QA_AGENT_NAME, "receipt_id": receipt_id},
        ).fetchone()
        if not row:
            return None
        decision_json = row[0] or {}
        receipt_payload = decision_json.get("receipt") if isinstance(decision_json, dict) else None
        if not receipt_payload:
            return None
        return EnforcementReceipt.model_validate(receipt_payload)


def resolve_receipt(
    *,
    request_id: Optional[str],
    receipt_id: Optional[str],
) -> tuple[Optional[EnforcementReceipt], Optional[str]]:
    try:
        receipt = _get_receipt_by_receipt_id(receipt_id) if receipt_id else None
        if receipt is None and request_id:
            receipt = _get_receipt_by_request_id(request_id)
        if receipt is None:
            return None, "ENFORCEMENT_RECEIPT_INVALID"
        return receipt, None
    except Exception as exc:
        logger.warning("receipt lookup failed: %s", exc)
        return None, "AUDIT_WRITE_FAILED"
