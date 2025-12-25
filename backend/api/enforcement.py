"""Enforcement receipt validation endpoints (Phase 10.1)."""
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from backend.features.enforcement.audit import (
    get_receipt_by_receipt_id,
    get_receipt_by_request_id,
)

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
        raise HTTPException(status_code=422, detail="request_id or receipt_id is required")

    receipt = None
    if body.receipt_id:
        receipt = get_receipt_by_receipt_id(body.receipt_id)
    if receipt is None and body.request_id:
        receipt = get_receipt_by_request_id(body.request_id)

    if receipt is None:
        return {
            "ok": False,
            "code": "RECEIPT_NOT_FOUND",
            "message": "No enforcement receipt found for the provided identifier.",
        }

    return {"ok": True, "receipt": receipt.model_dump(mode="json")}
