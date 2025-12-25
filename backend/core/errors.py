"""Error normalization and handlers (Phase 3.8)."""

import logging
import builtins
from typing import Optional
from uuid import uuid4

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

from backend.core.logging import get_request_id


class AppError(Exception):
    code = "app_error"
    status_code = 500

    def __init__(self, message: str, *, code: Optional[str] = None, status_code: Optional[int] = None, request_id: Optional[str] = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code
        self.request_id = request_id


class ValidationError(AppError, ValueError):
    code = "validation_error"
    status_code = 400


class NotFoundError(AppError, ValueError):
    code = "not_found"
    status_code = 404


class PermissionError(AppError, builtins.PermissionError):
    code = "forbidden"
    status_code = 403


class RingRequiredError(AppError):
    """Raised when user must hold the ring to perform an action."""
    code = "ring_required"
    status_code = 403


class ConflictError(AppError):
    code = "conflict"
    status_code = 409


class RateLimitError(AppError):
    code = "rate_limited"
    status_code = 429


class PayloadTooLargeError(AppError):
    code = "payload_too_large"
    status_code = 413


class QuotaExceededError(AppError):
    code = "quota_exceeded"
    status_code = 403


class LimitExceededError(AppError):
    code = "limit_exceeded"
    status_code = 429


class AdminAuditWriteError(AppError):
    code = "admin_audit_failed"
    status_code = 500


def _extract_request_id(request: Request, fallback: Optional[str] = None) -> str:
    return (
        getattr(request.state, "request_id", None)
        or get_request_id()
        or fallback
        or str(uuid4())
    )


def _error_payload(code: str, message: str, request_id: str) -> dict:
    return {
        "error": {"code": code, "message": message, "request_id": request_id},
        "detail": message,
    }


async def app_error_handler(request: Request, exc: AppError):
    rid = exc.request_id or _extract_request_id(request)
    payload = _error_payload(exc.code, exc.message, rid)
    logger = logging.getLogger("onering")
    log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
    logger.log(
        log_level,
        "app.error",
        extra={"request_id": rid, "error_code": exc.code, "error_message": exc.message, "status": exc.status_code},
    )
    response = JSONResponse(status_code=exc.status_code, content=payload)
    response.headers["x-request-id"] = rid
    return response


async def http_error_handler(request: Request, exc: HTTPException):
    rid = _extract_request_id(request)
    code = "not_found" if exc.status_code == 404 else "http_error"
    message = exc.detail if exc.detail else "HTTP error"
    payload = _error_payload(code, message, rid)
    logger = logging.getLogger("onering")
    logger.warning("http.error", extra={"request_id": rid, "error_code": code, "status": exc.status_code})
    response = JSONResponse(status_code=exc.status_code, content=payload)
    response.headers["x-request-id"] = rid
    return response


async def unhandled_exception_handler(request: Request, exc: Exception):
    rid = _extract_request_id(request)
    logger = logging.getLogger("onering")
    logger.error("unhandled.exception", exc_info=True, extra={"request_id": rid, "error_code": "internal_error"})
    payload = _error_payload("internal_error", "Unexpected error", rid)
    response = JSONResponse(status_code=500, content=payload)
    response.headers["x-request-id"] = rid
    return response
