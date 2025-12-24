"""
backend/api/realtime.py
WebSocket endpoint for real-time draft collaboration.

Phase 6.2: Implements /v1/ws/drafts/{draft_id} with Clerk JWT + X-User-Id auth.
Read-only socket; mutations must use REST endpoints (Phase 6.3 adds optimistic updates).
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime, timezone
import logging
import json

from backend.realtime.hub import hub
from backend.core.auth import verify_clerk_jwt

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
    
    # Accept connection first
    await websocket.accept()
    logger.debug(f"[WS] Accepted connection for draft {draft_id}")
    
    # Extract and validate authentication
    user_id = await _authenticate_websocket(websocket)
    
    if not user_id:
        await websocket.send_json({
            "type": "error",
            "message": "Unauthorized: missing or invalid authentication"
        })
        await websocket.close(code=1008, reason="Unauthorized")
        logger.debug(f"[WS] Rejected unauthenticated connection for draft {draft_id}")
        return
    
    logger.info(f"[WS] User {user_id} connected to draft {draft_id}")
    
    # Register in hub
    await hub.register(draft_id, websocket)
    
    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "draft_id": draft_id,
        "user_id": user_id,
        "ts": datetime.now(timezone.utc).isoformat()
    })
    
    # Message loop: receive pings, ignore other messages
    try:
        while True:
            try:
                data = await websocket.receive_json()
            except Exception as e:
                # Invalid JSON or connection lost
                logger.debug(f"[WS] Receive error for draft {draft_id}: {e}")
                break
            
            # Handle ping/pong keepalive
            if isinstance(data, dict) and data.get("type") == "ping":
                try:
                    await websocket.send_json({
                        "type": "pong",
                        "ts": datetime.now(timezone.utc).isoformat()
                    })
                except Exception as e:
                    logger.debug(f"[WS] Failed to send pong: {e}")
                    break
            # In Phase 6.2, ignore other messages (no mutations over WS)
            # Phase 6.3 will add optimistic updates over WS
    
    except WebSocketDisconnect:
        logger.info(f"[WS] User {user_id} disconnected from draft {draft_id}")
    except Exception as e:
        logger.error(f"[WS] Error in websocket loop for draft {draft_id}: {e}")
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
