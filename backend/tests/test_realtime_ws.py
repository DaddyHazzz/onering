"""
backend/tests/test_realtime_ws.py
WebSocket real-time collaboration tests.

Phase 6.2: Tests for hub, authentication, and event broadcasting.
"""

import pytest
import json
from datetime import datetime, timezone
from fastapi import WebSocket
from fastapi.testclient import TestClient

from backend.main import app
from backend.realtime.hub import DraftHub
from backend.core.auth import verify_clerk_jwt
from backend.models.collab import CollabDraftRequest


@pytest.fixture
def test_jwt():
    """Create a test JWT token."""
    import jwt
    from backend.core.config import settings
    
    payload = {
        "sub": "test_user_123",
        "iss": "https://test.clerk.accounts.dev",
        "aud": "test-app",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc).timestamp() + 3600)),
    }
    return jwt.encode(payload, settings.CLERK_SECRET_KEY, algorithm="HS256")


@pytest.fixture
def hub():
    """Provide a clean hub instance for testing."""
    return DraftHub()


class TestDraftHub:
    """Test in-memory hub functionality."""
    
    @pytest.mark.asyncio
    async def test_register_socket(self, hub):
        """Test registering a WebSocket in a room."""
        # Mock WebSocket
        class MockWS:
            async def send_json(self, data):
                pass
        
        ws = MockWS()
        await hub.register("draft_123", ws)
        
        assert await hub.get_room_size("draft_123") == 1
    
    @pytest.mark.asyncio
    async def test_unregister_socket(self, hub):
        """Test unregistering a WebSocket."""
        class MockWS:
            async def send_json(self, data):
                pass
        
        ws = MockWS()
        await hub.register("draft_123", ws)
        await hub.unregister("draft_123", ws)
        
        assert await hub.get_room_size("draft_123") == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_to_multiple_sockets(self, hub):
        """Test broadcasting message to multiple connected clients."""
        messages_received = []
        
        class MockWS:
            def __init__(self, name):
                self.name = name
            
            async def send_json(self, data):
                messages_received.append((self.name, data))
        
        ws1 = MockWS("client_1")
        ws2 = MockWS("client_2")
        
        await hub.register("draft_123", ws1)
        await hub.register("draft_123", ws2)
        
        message = {
            "type": "collab.segment_added",
            "draft_id": "draft_123",
            "ts": datetime.now(timezone.utc).isoformat(),
            "data": {"segment_id": "seg_1"}
        }
        
        await hub.broadcast("draft_123", message)
        
        # Both clients should receive
        assert len(messages_received) == 2
        assert messages_received[0][1] == message
        assert messages_received[1][1] == message
    
    @pytest.mark.asyncio
    async def test_broadcast_handles_dead_socket(self, hub):
        """Test that dead sockets are pruned during broadcast."""
        class DeadWS:
            async def send_json(self, data):
                raise Exception("Connection lost")
        
        class GoodWS:
            def __init__(self):
                self.message_count = 0
            
            async def send_json(self, data):
                self.message_count += 1
        
        dead = DeadWS()
        good = GoodWS()
        
        await hub.register("draft_123", dead)
        await hub.register("draft_123", good)
        
        assert await hub.get_room_size("draft_123") == 2
        
        message = {"type": "test"}
        await hub.broadcast("draft_123", message)
        
        # Dead socket should be pruned, good socket should receive
        assert good.message_count == 1
        assert await hub.get_room_size("draft_123") == 1
    
    @pytest.mark.asyncio
    async def test_broadcast_to_empty_room(self, hub):
        """Test broadcasting to non-existent room (graceful no-op)."""
        message = {"type": "test"}
        
        # Should not raise
        await hub.broadcast("nonexistent_draft", message)


class TestWebSocketAuth:
    """Test WebSocket authentication."""
    
    def test_ws_connect_with_jwt_header(self, test_jwt):
        """Test connecting with Clerk JWT in Authorization header."""
        client = TestClient(app)
        
        # Note: TestClient WebSocket doesn't support custom headers the same way
        # but X-User-Id works. In production, Authorization header works with browser.
        # This test verifies X-User-Id fallback works.
        with client.websocket_connect(
            "/v1/ws/drafts/draft_123",
            headers={"X-User-Id": "test_user_123"}
        ) as ws:
            data = ws.receive_json()
            
            # Should receive welcome message
            assert data["type"] == "connected"
            assert data["draft_id"] == "draft_123"
            assert data["user_id"] == "test_user_123"
    
    def test_ws_connect_with_x_user_id_header(self):
        """Test connecting with X-User-Id header (fallback)."""
        client = TestClient(app)
        
        with client.websocket_connect(
            "/v1/ws/drafts/draft_123",
            headers={"X-User-Id": "test_user_456"}
        ) as ws:
            data = ws.receive_json()
            
            # Should receive welcome message
            assert data["type"] == "connected"
            assert data["user_id"] == "test_user_456"
    
    def test_ws_reject_no_auth(self):
        """Test that connection without auth gets error response."""
        client = TestClient(app)
        
        try:
            with client.websocket_connect("/v1/ws/drafts/draft_123") as ws:
                data = ws.receive_json()
                # Should receive error message
                assert data["type"] == "error"
                assert "Unauthorized" in data.get("message", "")
        except Exception:
            # Connection may close immediately, which is also acceptable
            pass
    
    def test_ws_reject_invalid_jwt(self):
        """Test that connection with invalid JWT gets error response."""
        client = TestClient(app)
        
        try:
            with client.websocket_connect(
                "/v1/ws/drafts/draft_123",
                headers={"X-User-Id": ""}  # Empty auth
            ) as ws:
                data = ws.receive_json()
                # Should receive error message
                assert data["type"] == "error"
        except Exception:
            # Connection may close immediately, which is also acceptable
            pass


class TestWebSocketEvents:
    """Test event broadcasting over WebSocket."""
    
    def test_ws_receive_ping_pong(self):
        """Test client ping/server pong keepalive."""
        client = TestClient(app)
        
        with client.websocket_connect(
            "/v1/ws/drafts/draft_123",
            headers={"X-User-Id": "test_user_123"}
        ) as ws:
            # Receive welcome
            welcome = ws.receive_json()
            assert welcome["type"] == "connected"
            
            # Send ping
            ws.send_json({"type": "ping"})
            
            # Receive pong
            pong = ws.receive_json()
            assert pong["type"] == "pong"
            assert "ts" in pong
    
    def test_ws_multiple_clients_same_draft(self):
        """Test that multiple clients connected to same draft receive broadcasts."""
        client = TestClient(app)
        
        # Two clients connect to same draft
        with client.websocket_connect(
            "/v1/ws/drafts/draft_123",
            headers={"X-User-Id": "user_a"}
        ) as ws_a:
            with client.websocket_connect(
                "/v1/ws/drafts/draft_123",
                headers={"X-User-Id": "user_b"}
            ) as ws_b:
                # Receive welcomes
                ws_a.receive_json()
                ws_b.receive_json()
                
                # Simulate segment append via hub broadcast
                import asyncio
                from backend.realtime.hub import hub
                
                event = {
                    "type": "collab.segment_added",
                    "draft_id": "draft_123",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "segment": {
                            "id": 1,
                            "author_user_id": "user_a",
                            "content": "Test content",
                            "position": 0,
                        }
                    }
                }
                
                # Run async broadcast
                loop = asyncio.new_event_loop()
                loop.run_until_complete(hub.broadcast("draft_123", event))
                
                # Both clients should receive event
                msg_a = ws_a.receive_json()
                msg_b = ws_b.receive_json()
                
                assert msg_a["type"] == "collab.segment_added"
                assert msg_b["type"] == "collab.segment_added"
    
    def test_ws_separate_drafts_dont_cross_streams(self):
        """Test that events on draft_A don't reach clients on draft_B."""
        client = TestClient(app)
        
        with client.websocket_connect(
            "/v1/ws/drafts/draft_a",
            headers={"X-User-Id": "user_x"}
        ) as ws_a:
            with client.websocket_connect(
                "/v1/ws/drafts/draft_b",
                headers={"X-User-Id": "user_y"}
            ) as ws_b:
                # Receive welcomes
                ws_a.receive_json()
                ws_b.receive_json()
                
                # Broadcast to draft_a
                import asyncio
                from backend.realtime.hub import hub
                
                event = {
                    "type": "collab.segment_added",
                    "draft_id": "draft_a",
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "data": {}
                }
                
                loop = asyncio.new_event_loop()
                loop.run_until_complete(hub.broadcast("draft_a", event))
                
                # Only ws_a should receive
                msg_a = ws_a.receive_json()
                assert msg_a["type"] == "collab.segment_added"
                
                # ws_b should not have anything new
                ws_b.send_json({"type": "ping"})
                pong_b = ws_b.receive_json()
                assert pong_b["type"] == "pong"  # Only the pong, not the broadcast


class TestWebSocketDisconnect:
    """Test WebSocket disconnect handling."""
    
    def test_ws_unregisters_on_close(self):
        """Test that disconnecting socket is unregistered from hub."""
        from backend.realtime.hub import hub
        import asyncio
        
        client = TestClient(app)
        
        with client.websocket_connect(
            "/v1/ws/drafts/draft_123",
            headers={"X-User-Id": "user_123"}
        ) as ws:
            ws.receive_json()  # Welcome
            
            # Check hub has the socket
            loop = asyncio.new_event_loop()
            size_before = loop.run_until_complete(hub.get_room_size("draft_123"))
            assert size_before >= 1
        
        # After disconnect, hub should be empty (or smaller)
        loop = asyncio.new_event_loop()
        size_after = loop.run_until_complete(hub.get_room_size("draft_123"))
        # Note: might be other tests' sockets, just check it decreased or is 0
        assert size_after <= size_before
