"""
backend/realtime/hub.py
In-memory pubsub hub for draft collaboration.

Single instance broadcasts events to all WebSocket clients subscribed to a draft room.
Thread-safe with proper cleanup of dead sockets.
"""

from typing import Dict, Set
from fastapi import WebSocket
import asyncio
import logging

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
        # Lock for thread-safe access
        self._lock = asyncio.Lock()
    
    async def register(self, draft_id: str, websocket: WebSocket) -> None:
        """
        Register WebSocket in draft room.
        
        Args:
            draft_id: Draft identifier
            websocket: Connected WebSocket client
        """
        async with self._lock:
            if draft_id not in self._rooms:
                self._rooms[draft_id] = set()
            self._rooms[draft_id].add(websocket)
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
                
                # Clean up empty rooms
                if not self._rooms[draft_id]:
                    del self._rooms[draft_id]
                    logger.debug(f"[HUB] Cleaned up empty room for draft {draft_id}")
                else:
                    logger.debug(f"[HUB] Unregistered socket for draft {draft_id}. Remaining: {len(self._rooms[draft_id])}")
    
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


# Global singleton hub instance
hub = DraftHub()
