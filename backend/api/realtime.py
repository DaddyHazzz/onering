"""
backend/api/realtime.py
WebSocket endpoint for real-time draft collaboration.

Phase 6.2: Implements /v1/ws/drafts/{draft_id} with Clerk JWT + X-User-Id auth.
Read-only socket; mutations must use REST endpoints (Phase 6.3 adds optimistic updates).
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
from uuid import uuid4
import logging
import json

from backend.realtime.hub import hub
from backend.core.auth import verify_clerk_jwt
from backend.core.logging import log_event
from backend.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/v1/ws/drafts/{draft_id}")
async def websocket_endpoint(websocket: WebSocket, draft_id: str):
    """
    Real-time collaboration WebSocket endpoint.
    
    Auth Methods:
    1. Authorization: Bearer <Clerk JWT>
    2. X-User-Id: <user_id> (fallback/tests)
    
    Events Emitted:
    - collab.segment_added
    - collab.ring_passed
    - collab.collaborator_added
    
    Client Behavior:
    - Subscribe on connect (automatic)
    - Send "ping" to keep alive
    - Receive events asynchronously
    - Graceful reconnect if disconnected
    
    Phase 6.2: Read-only socket (mutations via REST).
    """
    
    await websocket.accept()
    request_id = websocket.headers.get("X-Request-Id") or str(uuid4())
    connection_id = str(uuid4())
    limits_enabled = bool(settings.WS_LIMITS_ENABLED)
    logger.debug(f"[WS] Accepted connection for draft {draft_id}")

    # Origin check (if limits enabled and not wildcard)
    if limits_enabled:
        origin = websocket.headers.get("origin")
        allowed = [o.strip() for o in settings.WS_ALLOWED_ORIGINS.split(",") if o.strip()]
        if allowed and allowed != ["*"] and (not origin or origin not in allowed):
            log_event("info", "ws.origin_blocked", request_id=request_id, user_id=None, draft_id=draft_id, event_type="ws.origin_blocked", extra={"origin": origin, "connection_id": connection_id})
            await _reject_and_close(websocket, request_id, "ws_limit", "Origin not allowed")
            return
    
    # Extract and validate authentication
    user_id = await _authenticate_websocket(websocket)
    
    if not user_id:
        await _reject_and_close(
            websocket,
            request_id,
            "forbidden",
            "Unauthorized: missing or invalid authentication",
        )
        log_event(
            "info",
            "ws.unauthorized",
            request_id=request_id,
            user_id=None,
            draft_id=draft_id,
            event_type="ws.unauthorized",
            extra={"connection_id": connection_id},
        )
        return
    
    log_event(
        "info",
        "ws.connected",
        request_id=request_id,
        user_id=user_id,
        draft_id=draft_id,
        event_type="ws.connected",
        extra={"connection_id": connection_id},
    )
    
    # Enforce WS limits before registering
    if limits_enabled:
        counts = await hub.get_counts(draft_id, user_id)
        if counts["global"] >= settings.WS_MAX_SOCKETS_GLOBAL:
            log_event("info", "ws.limit.global", request_id=request_id, user_id=user_id, draft_id=draft_id, event_type="ws.limit.global", extra={"connection_id": connection_id})
            await _reject_and_close(websocket, request_id, "ws_limit", "Global socket limit exceeded")
            return
        if counts["draft"] >= settings.WS_MAX_SOCKETS_PER_DRAFT:
            log_event("info", "ws.limit.draft", request_id=request_id, user_id=user_id, draft_id=draft_id, event_type="ws.limit.draft", extra={"connection_id": connection_id})
            await _reject_and_close(websocket, request_id, "ws_limit", "Draft socket limit exceeded")
            return
        if counts["user"] >= settings.WS_MAX_SOCKETS_PER_USER:
            log_event("info", "ws.limit.user", request_id=request_id, user_id=user_id, draft_id=draft_id, event_type="ws.limit.user", extra={"connection_id": connection_id})
            await _reject_and_close(websocket, request_id, "ws_limit", "User socket limit exceeded")
            return
    if settings.MAX_WS_CONNECTIONS_PER_DRAFT and settings.MAX_WS_CONNECTIONS_PER_DRAFT > 0:
        draft_counts = await hub.get_counts(draft_id, user_id)
        if draft_counts["draft"] >= settings.MAX_WS_CONNECTIONS_PER_DRAFT:
            log_event("warning", "ws.scale_cap.draft", request_id=request_id, user_id=user_id, draft_id=draft_id, event_type="ws.scale_cap.draft", extra={"connection_id": connection_id, "cap": settings.MAX_WS_CONNECTIONS_PER_DRAFT})
            await _reject_and_close(websocket, request_id, "limit_exceeded", "Draft connection cap exceeded")
            return

    # Register in hub
    await hub.register(draft_id, websocket, user_id=user_id)
    
    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "draft_id": draft_id,
        "user_id": user_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "connection_id": connection_id,
    })
    
    # Message loop: receive pings, ignore other messages
    try:
        while True:
            try:
                raw_message = await websocket.receive_text()
                if limits_enabled:
                    if len(raw_message.encode("utf-8")) > settings.WS_MAX_MESSAGE_BYTES:
                        log_event("info", "ws.payload_too_large", request_id=request_id, user_id=user_id, draft_id=draft_id, event_type="ws.payload_too_large", extra={"connection_id": connection_id})
                        await _reject_and_close(websocket, request_id, "payload_too_large", "WS message too large")
                        break
                try:
                    data = json.loads(raw_message)
                except Exception as e:
                    log_event(
                        "debug",
                        "ws.invalid_json",
                        request_id=request_id,
                        user_id=user_id,
                        draft_id=draft_id,
                        event_type="ws.invalid_json",
                        extra={"error": str(e), "connection_id": connection_id},
                    )
                    break
            except Exception as e:
                # Invalid JSON or connection lost
                log_event(
                    "debug",
                        "ws.receive_error",
                        request_id=request_id,
                        user_id=user_id,
                        draft_id=draft_id,
                        event_type="ws.receive_error",
                        extra={"error": str(e), "connection_id": connection_id},
                )
                break
            
            # Handle ping/pong keepalive
            if isinstance(data, dict) and data.get("type") == "ping":
                try:
                    await websocket.send_json({
                        "type": "pong",
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "request_id": request_id,
                    })
                except Exception as e:
                    log_event(
                        "debug",
                        "ws.pong_failed",
                        request_id=request_id,
                        user_id=user_id,
                        draft_id=draft_id,
                        event_type="ws.pong_failed",
                        extra={"error": str(e), "connection_id": connection_id},
                    )
                    break
            # In Phase 6.2, ignore other messages (no mutations over WS)
            # Phase 6.3 will add optimistic updates over WS
    
    except WebSocketDisconnect:
        log_event(
            "info",
            "ws.disconnected",
            request_id=request_id,
            user_id=user_id,
            draft_id=draft_id,
            event_type="ws.disconnected",
            extra={"connection_id": connection_id},
        )
    except Exception as e:
        log_event(
            "error",
            "ws.loop_error",
            request_id=request_id,
            user_id=user_id,
            draft_id=draft_id,
            event_type="ws.loop_error",
            extra={"error": str(e), "connection_id": connection_id},
        )
    finally:
        # Cleanup: unregister from hub
        await hub.unregister(draft_id, websocket)


async def _authenticate_websocket(websocket: WebSocket) -> str | None:
    """
    Authenticate WebSocket connection.
    
    Tries in order:
    1. Clerk JWT from Authorization header
    2. X-User-Id from headers (fallback/tests)
    
    Returns:
        user_id if authenticated, None otherwise
    """
    # Try Clerk JWT first
    auth_header = websocket.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:]
        try:
            user_id = verify_clerk_jwt(jwt_token)
            if user_id:
                logger.debug(f"[WS] Authenticated via Clerk JWT: {user_id}")
                return user_id
        except Exception as e:
            logger.debug(f"[WS] JWT validation failed: {e}")
    
    # Fallback to X-User-Id header (tests)
    user_id = websocket.headers.get("X-User-Id")
    if user_id:
        logger.debug(f"[WS] Authenticated via X-User-Id header: {user_id}")
        return user_id
    
    return None


async def _reject_and_close(websocket: WebSocket, request_id: str, code: str, message: str):
    try:
        await websocket.send_json({
            "type": "error",
            "code": code,
            "message": message,
            "request_id": request_id,
        })
    except Exception:
        pass
    try:
        await websocket.close(code=1008, reason=message)
    except Exception:
        pass
