"""
Phase 10.2: Publish -> Ledger integration.

Persists publish events and issues tokens (shadow/live) with idempotency.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.features.enforcement.audit import resolve_receipt, resolve_qa_details
from backend.features.enforcement.contracts import EnforcementReceipt
from backend.features.tokens.ledger import issue_ring_for_publish, get_token_issuance_mode


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _find_existing_publish_event(db: Session, event_id: str) -> Optional[Dict]:
    row = db.execute(
        text(
            """
            SELECT id, token_mode, token_issued_amount, token_pending_amount, token_reason_code,
                   token_ledger_id, token_pending_id
            FROM publish_events
            WHERE id = :event_id
            """
        ),
        {"event_id": event_id},
    ).fetchone()
    if not row:
        return None
    return {
        "event_id": row[0],
        "token_mode": row[1],
        "token_issued_amount": row[2],
        "token_pending_amount": row[3],
        "token_reason_code": row[4],
        "token_ledger_id": row[5],
        "token_pending_id": row[6],
    }


def _find_existing_issuance(db: Session, event_id: str) -> Tuple[Optional[str], Optional[str]]:
    ledger_row = db.execute(
        text(
            """
            SELECT id
            FROM ring_ledger
            WHERE metadata->>'publish_event_id' = :event_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"event_id": event_id},
    ).fetchone()
    pending_row = db.execute(
        text(
            """
            SELECT id
            FROM ring_pending
            WHERE metadata->>'publish_event_id' = :event_id
            ORDER BY created_at DESC
            LIMIT 1
            """
        ),
        {"event_id": event_id},
    ).fetchone()
    return (str(ledger_row[0]) if ledger_row else None, str(pending_row[0]) if pending_row else None)


def _persist_publish_event(
    db: Session,
    *,
    event_id: str,
    user_id: str,
    platform: str,
    content_hash: str,
    published_at: datetime,
    platform_post_id: Optional[str],
    enforcement_request_id: Optional[str],
    enforcement_receipt_id: Optional[str],
    qa_status: Optional[str],
    violation_codes: Optional[list],
    audit_ok: bool,
    metadata: Optional[Dict],
    token_mode: Optional[str],
    token_issued_amount: Optional[int],
    token_pending_amount: Optional[int],
    token_reason_code: Optional[str],
    token_ledger_id: Optional[str],
    token_pending_id: Optional[str],
) -> None:
    db.execute(
        text(
            """
            INSERT INTO publish_events
            (id, user_id, platform, content_hash, published_at, platform_post_id,
             enforcement_request_id, enforcement_receipt_id, qa_status, violation_codes, audit_ok,
             metadata, token_mode, token_issued_amount, token_pending_amount, token_reason_code,
             token_ledger_id, token_pending_id)
            VALUES
            (:id, :user_id, :platform, :content_hash, :published_at, :platform_post_id,
             :enforcement_request_id, :enforcement_receipt_id, :qa_status, CAST(:violation_codes AS jsonb), :audit_ok,
             CAST(:metadata AS jsonb), :token_mode, :token_issued_amount, :token_pending_amount, :token_reason_code,
             :token_ledger_id, :token_pending_id)
            """
        ),
        {
            "id": event_id,
            "user_id": user_id,
            "platform": platform,
            "content_hash": content_hash,
            "published_at": published_at,
            "platform_post_id": platform_post_id,
            "enforcement_request_id": enforcement_request_id,
            "enforcement_receipt_id": enforcement_receipt_id,
            "qa_status": qa_status,
            "violation_codes": json.dumps(violation_codes or []),
            "audit_ok": audit_ok,
            "metadata": json.dumps(metadata or {}),
            "token_mode": token_mode,
            "token_issued_amount": token_issued_amount,
            "token_pending_amount": token_pending_amount,
            "token_reason_code": token_reason_code,
            "token_ledger_id": token_ledger_id,
            "token_pending_id": token_pending_id,
        },
    )
    db.commit()


def _validate_receipt(
    *,
    request_id: Optional[str],
    receipt_id: Optional[str],
) -> Tuple[Optional[EnforcementReceipt], Optional[str], Optional[dict]]:
    if not request_id and not receipt_id:
        return None, "ENFORCEMENT_RECEIPT_REQUIRED", None

    receipt, error_code = resolve_receipt(request_id=request_id, receipt_id=receipt_id)
    if error_code or not receipt:
        return None, error_code or "ENFORCEMENT_RECEIPT_INVALID", None

    now = datetime.now(timezone.utc)
    if receipt.expires_at and receipt.expires_at < now:
        return None, "ENFORCEMENT_RECEIPT_EXPIRED", None

    qa_details, qa_error = resolve_qa_details(request_id=request_id, receipt_id=receipt_id)
    if qa_error:
        qa_details = None
    return receipt, None, qa_details


def handle_publish_event(
    db: Session,
    *,
    event_id: str,
    user_id: str,
    platform: str,
    content_hash: str,
    published_at: datetime,
    platform_post_id: Optional[str],
    enforcement_request_id: Optional[str],
    enforcement_receipt_id: Optional[str],
    metadata: Optional[Dict],
) -> Dict:
    started_at = datetime.now(timezone.utc)
    existing = _find_existing_publish_event(db, event_id)
    if existing:
        return {
            "ok": True,
            "event_id": existing["event_id"],
            "token_result": {
                "mode": existing["token_mode"] or "off",
                "issued_amount": existing["token_issued_amount"] or 0,
                "pending_amount": existing["token_pending_amount"] or 0,
                "reason_code": existing["token_reason_code"] or "IDEMPOTENT_REPLAY",
                "guardrails_applied": [],
                "ledger_id": existing["token_ledger_id"],
                "pending_id": existing["token_pending_id"],
            },
        }

    token_mode = get_token_issuance_mode()
    reason_code = None
    issued_amount = 0
    pending_amount = 0
    ledger_id = None
    pending_id = None
    guardrails = []

    receipt, receipt_error, qa_details = _validate_receipt(
        request_id=enforcement_request_id,
        receipt_id=enforcement_receipt_id,
    )
    qa_status = qa_details.get("status") if isinstance(qa_details, dict) else (receipt.qa_status if receipt else None)
    violation_codes = qa_details.get("violation_codes") if isinstance(qa_details, dict) else []
    audit_ok = receipt_error is None and receipt is not None

    if token_mode == "off":
        reason_code = "TOKEN_ISSUANCE_OFF"
    elif receipt_error:
        reason_code = receipt_error
    elif qa_status != "PASS":
        reason_code = "QA_NOT_PASS"
    elif not audit_ok:
        reason_code = "AUDIT_NOT_OK"
    elif not platform_post_id:
        reason_code = "PLATFORM_CONFIRMATION_MISSING"
    else:
        existing_ledger_id, existing_pending_id = _find_existing_issuance(db, event_id)
        if existing_ledger_id or existing_pending_id:
            ledger_id = existing_ledger_id
            pending_id = existing_pending_id
            reason_code = "IDEMPOTENT_REPLAY"
        else:
            issue = issue_ring_for_publish(
                db,
                user_id,
                None,
                enforcement_request_id,
                enforcement_receipt_id,
                qa_status=qa_status or "FAIL",
                audit_ok=audit_ok,
                platform=platform,
                metadata={
                    "publish_event_id": event_id,
                    "platform_post_id": platform_post_id,
                    "content_hash": content_hash,
                    **(metadata or {}),
                },
            )
            guardrails = issue.get("violations", []) or []
            if token_mode == "shadow":
                pending_amount = issue.get("amount", 0) or 0
                pending_id = issue.get("pending_id")
                reason_code = "PENDING" if pending_amount > 0 else "GUARDRAIL_BLOCKED"
            elif token_mode == "live":
                issued_amount = issue.get("amount", 0) or 0
                ledger_id = issue.get("ledger_id")
                reason_code = "ISSUED" if issue.get("issued") else "GUARDRAIL_BLOCKED"

    meta = metadata or {}
    meta["issuance_latency_ms"] = int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)

    _persist_publish_event(
        db,
        event_id=event_id,
        user_id=user_id,
        platform=platform,
        content_hash=content_hash,
        published_at=published_at,
        platform_post_id=platform_post_id,
        enforcement_request_id=enforcement_request_id,
        enforcement_receipt_id=enforcement_receipt_id,
        qa_status=qa_status,
        violation_codes=violation_codes or [],
        audit_ok=audit_ok,
        metadata=meta,
        token_mode=token_mode,
        token_issued_amount=issued_amount if issued_amount else None,
        token_pending_amount=pending_amount if pending_amount else None,
        token_reason_code=reason_code,
        token_ledger_id=ledger_id,
        token_pending_id=pending_id,
    )

    return {
        "ok": True,
        "event_id": event_id,
        "token_result": {
            "mode": token_mode,
            "issued_amount": issued_amount,
            "pending_amount": pending_amount,
            "reason_code": reason_code,
            "guardrails_applied": guardrails,
            "ledger_id": ledger_id,
            "pending_id": pending_id,
        },
    }
