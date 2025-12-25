"""Enforcement receipt validation endpoints (Phase 10.1)."""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from backend.features.enforcement.audit import resolve_receipt

router = APIRouter(prefix="/v1/enforcement", tags=["enforcement"])


class ReceiptValidateRequest(BaseModel):
    request_id: Optional[str] = None
    receipt_id: Optional[str] = None

    @field_validator("request_id", "receipt_id")
    @classmethod
    def _trim(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip() or None


@router.post("/receipts/validate")
async def validate_receipt(body: ReceiptValidateRequest):
    if not body.request_id and not body.receipt_id:
        return {
            "ok": False,
            "code": "ENFORCEMENT_RECEIPT_REQUIRED",
            "message": "request_id or receipt_id is required",
        }

    receipt, error_code = resolve_receipt(request_id=body.request_id, receipt_id=body.receipt_id)
    if error_code:
        payload = {
            "ok": False,
            "code": error_code,
            "message": "Enforcement receipt lookup failed",
        }
        if error_code == "AUDIT_WRITE_FAILED":
            payload["suggestedFix"] = "Ensure audit tables are created before enabling enforced mode."
        return payload

    now = datetime.now(timezone.utc)
    if receipt.expires_at and receipt.expires_at < now:
        return {
            "ok": False,
            "code": "ENFORCEMENT_RECEIPT_EXPIRED",
            "message": "Enforcement receipt has expired",
            "suggestedFix": "Regenerate content with enforcement enabled to obtain a fresh receipt.",
        }

    if receipt.qa_status != "PASS":
        return {
            "ok": False,
            "code": "ENFORCEMENT_RECEIPT_INVALID",
            "message": "Enforcement receipt does not permit publishing",
        }

    return {"ok": True, "receipt": receipt.model_dump(mode="json")}
