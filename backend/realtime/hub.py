"""
backend/realtime/hub.py
In-memory pubsub hub for draft collaboration.

Single instance broadcasts events to all WebSocket clients subscribed to a draft room.
Thread-safe with proper cleanup of dead sockets.
"""

from typing import Dict, Set, Tuple, Optional
from fastapi import WebSocket
import asyncio
import logging

from backend.core.metrics import (
    drafts_active_rooms,
    ws_active_connections,
    ws_connections_total,
    ws_messages_sent_total,
)

logger = logging.getLogger(__name__)


class DraftHub:
    """
    In-memory room-per-draft broadcast hub.
    
    Maps draft_id -> Set[WebSocket], allows safe concurrent access.
    Handles WebSocket lifecycle: register, broadcast, unregister.
    """
    
    def __init__(self):
        # draft_id -> set of connected WebSockets
        self._rooms: Dict[str, Set[WebSocket]] = {}
        # websocket -> (draft_id, user_id)
        self._connections: Dict[WebSocket, Tuple[str, Optional[str]]] = {}
        # user_id -> count
        self._user_counts: Dict[str, int] = {}
        self._global_count: int = 0
        # Lock for thread-safe access
        self._lock = asyncio.Lock()
    
    async def register(self, draft_id: str, websocket: WebSocket, user_id: Optional[str] = None) -> None:
        """
        Register WebSocket in draft room.
        
        Args:
            draft_id: Draft identifier
            websocket: Connected WebSocket client
            user_id: Optional user identifier for limits/metrics
        """
        async with self._lock:
            if draft_id not in self._rooms:
                self._rooms[draft_id] = set()
            self._rooms[draft_id].add(websocket)
            self._connections[websocket] = (draft_id, user_id)
            if user_id:
                self._user_counts[user_id] = self._user_counts.get(user_id, 0) + 1
            self._global_count += 1
            ws_connections_total.inc()
            ws_active_connections.set(self._global_count)
            drafts_active_rooms.set(len(self._rooms))
            logger.debug(f"[HUB] Registered socket for draft {draft_id}. Total: {len(self._rooms[draft_id])}")
    
    async def unregister(self, draft_id: str, websocket: WebSocket) -> None:
        """
        Unregister WebSocket from draft room.
        
        Args:
            draft_id: Draft identifier
            websocket: WebSocket client to unregister
        """
        async with self._lock:
            if draft_id in self._rooms:
                self._rooms[draft_id].discard(websocket)
                meta = self._connections.pop(websocket, None)
                if meta:
                    _, user_id = meta
                    if user_id and self._user_counts.get(user_id):
                        self._user_counts[user_id] = max(0, self._user_counts[user_id] - 1)
                        if self._user_counts[user_id] == 0:
                            del self._user_counts[user_id]
                self._global_count = max(0, self._global_count - 1)
                
                # Clean up empty rooms
                if not self._rooms[draft_id]:
                    del self._rooms[draft_id]
                    logger.debug(f"[HUB] Cleaned up empty room for draft {draft_id}")
                else:
                    logger.debug(f"[HUB] Unregistered socket for draft {draft_id}. Remaining: {len(self._rooms[draft_id])}")
            ws_active_connections.set(self._global_count)
            drafts_active_rooms.set(len(self._rooms))
    
    async def broadcast(self, draft_id: str, message: dict) -> None:
        """
        Broadcast message to all WebSockets in a draft room.
        
        Handles connection failures gracefully by pruning dead sockets.
        
        Args:
            draft_id: Draft identifier
            message: JSON-serializable message dict
        """
        async with self._lock:
            if draft_id not in self._rooms or not self._rooms[draft_id]:
                return  # No subscribers
            
            # Copy set to avoid modification during iteration
            sockets = self._rooms[draft_id].copy()
        
        dead_sockets = []
        for ws in sockets:
            try:
                event_type = message.get("type") if isinstance(message, dict) else "unknown"
                ws_messages_sent_total.inc(labels={"event_type": str(event_type) if event_type else "unknown"})
                await ws.send_json(message)
            except Exception as e:
                logger.debug(f"[HUB] Failed to send to socket: {e}")
                dead_sockets.append(ws)
        
        # Prune dead sockets
        if dead_sockets:
            async with self._lock:
                for ws in dead_sockets:
                    self._rooms[draft_id].discard(ws)
                logger.debug(f"[HUB] Pruned {len(dead_sockets)} dead sockets from draft {draft_id}")
    
    async def get_room_size(self, draft_id: str) -> int:
        """Get number of connected clients in a room."""
        async with self._lock:
            return len(self._rooms.get(draft_id, set()))

    async def get_counts(self, draft_id: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, int]:
        """Return current connection counts for policy checks."""
        async with self._lock:
            return {
                "global": self._global_count,
                "draft": len(self._rooms.get(draft_id, set())) if draft_id else 0,
                "user": self._user_counts.get(user_id, 0) if user_id else 0,
            }


# Global singleton hub instance
hub = DraftHub()
