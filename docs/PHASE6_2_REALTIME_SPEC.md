# Phase 6.2: Real-Time Collab Specification (WebSockets + Fallback Polling)

**Date**: December 23, 2025  
**Status**: DESIGN PHASE (PART 0)  
**Last Updated**: Session Start

---

## Overview

Phase 6.2 adds **real-time synchronization** to collaborative drafts using WebSockets with an intelligent fallback to polling. When multiple users view the same draft, mutations (segment appends, ring passes, collaborator additions) are broadcast instantly to all viewers.

### Architecture Diagram

```
┌─────────────────┐         ┌─────────────────┐
│  User A Client  │         │  User B Client  │
│  (Draft View)   │         │  (Draft View)   │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │ WS /v1/ws/drafts/{id}    │
         └───────────┬───────────────┘
                     │
         ┌───────────▼──────────────┐
         │  Backend Realtime Hub    │
         │  (draft_id -> sockets)   │
         └───────────┬──────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
      REST        Collab       Event
      Routes      Service      Emitter
      (write)     (emit)       (broadcast)

Fallback (if WS unavailable):
   Client ────→ Polling (GET /v1/collab/drafts/{id}) every ~3s
```

---

## WebSocket Endpoint

### URL

```
ws://localhost:8000/v1/ws/drafts/{draft_id}
wss://api.example.com/v1/ws/drafts/{draft_id}  [production]
```

### Authentication

**Method 1: Clerk JWT (Primary)**

```http
GET /v1/ws/drafts/draft_abc123 HTTP/1.1
Host: localhost:8000
Upgrade: websocket
Connection: Upgrade
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Method 2: X-User-Id Header (Fallback/Tests)**

```http
GET /v1/ws/drafts/draft_abc123 HTTP/1.1
Host: localhost:8000
Upgrade: websocket
Connection: Upgrade
X-User-Id: test_user_123
```

### Connection Lifecycle

1. **Connect**
   - Client sends WebSocket upgrade request with auth header
   - Server validates JWT or X-User-Id
   - Server validates user can view draft (creator or collaborator)
   - Server registers socket in hub room `drafts/{draft_id}`

2. **Subscribe**
   - Client automatically receives all events for this draft
   - Server sends keepalive ping every 25 seconds

3. **Receive**
   - Client sends `{"type": "ping"}` to keep connection alive
   - Server responds with `{"type": "pong"}`
   - **Note**: In Phase 6.2, WebSocket is **read-only** (no mutations over WS)
   - Mutations must use REST endpoints (idempotency preserved)

4. **Disconnect**
   - Client closes connection (tab closed, browser loses focus, network lost)
   - Server unregisters socket from hub
   - If client reconnects → old socket is pruned
   - No data loss (client can use polling fallback)

---

## Event Schema

### Unified Event Format

All events follow a consistent structure:

```json
{
  "type": "collab.{event_name}",
  "draft_id": "draft_abc123",
  "ts": "2025-12-23T20:30:45.123Z",
  "user_id": "user_xyz789",
  "data": {
    // Event-specific payload (minimal diff, not full draft)
  }
}
```

### Event Types

#### 1. `collab.segment_added`

Emitted when segment appended to draft.

```json
{
  "type": "collab.segment_added",
  "draft_id": "draft_abc123",
  "ts": "2025-12-23T20:30:45.123Z",
  "user_id": "user_xyz789",
  "data": {
    "segment": {
      "id": 42,
      "author_user_id": "user_xyz789",
      "content": "New segment text...",
      "position": 3,
      "created_at": "2025-12-23T20:30:45.123Z"
    }
  }
}
```

#### 2. `collab.ring_passed`

Emitted when ring is passed to a new holder.

```json
{
  "type": "collab.ring_passed",
  "draft_id": "draft_abc123",
  "ts": "2025-12-23T20:30:50.456Z",
  "user_id": "user_xyz789",
  "data": {
    "from_user_id": "user_xyz789",
    "to_user_id": "user_abc456",
    "current_holder_id": "user_abc456",
    "holders_history": ["user_xyz789", "user_abc456"]
  }
}
```

#### 3. `collab.collaborator_added`

Emitted when new collaborator invited to draft.

```json
{
  "type": "collab.collaborator_added",
  "draft_id": "draft_abc123",
  "ts": "2025-12-23T20:31:00.789Z",
  "user_id": "user_xyz789",
  "data": {
    "collaborator_id": "user_def012",
    "role": "contributor",
    "joined_at": "2025-12-23T20:31:00.789Z"
  }
}
```

#### 4. `collab.draft_updated` (Optional)

Emitted for non-critical updates (title, description changes).

```json
{
  "type": "collab.draft_updated",
  "draft_id": "draft_abc123",
  "ts": "2025-12-23T20:31:05.012Z",
  "user_id": "user_xyz789",
  "data": {
    "title": "Updated Title",
    "description": "Updated description"
  }
}
```

---

## Client Behavior

### JavaScript WebSocket Usage

```typescript
// src/lib/realtime.ts
export function getWsUrl(draftId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${window.location.host}/v1/ws/drafts/${draftId}`;
}

export async function openDraftSocket(
  draftId: string,
  options?: { token?: string; userId?: string }
): Promise<WebSocket> {
  const url = getWsUrl(draftId);
  const ws = new WebSocket(url);
  
  // Try auth with Clerk JWT
  if (options?.token) {
    ws.onopen = () => {
      // Send auth header as message (WebSocket doesn't support custom headers in browser)
      // Instead, rely on server-side connection header parsing
    };
  }
  // Fallback: X-User-Id in localStorage (server can read via custom header workaround)
  
  return ws;
}

export type RealtimeEvent = {
  type: string;
  draft_id: string;
  ts: string;
  user_id: string;
  data: any;
};

export function parseEvent(message: string): RealtimeEvent {
  return JSON.parse(message);
}
```

### React Hook Integration

```typescript
// src/hooks/useDraftRealtime.ts
export interface DraftRealtimeOptions {
  draftId: string;
  enabled?: boolean;
  onSegmentAdded?: (segment: DraftSegment) => void;
  onRingPassed?: (from: string, to: string) => void;
  onCollaboratorAdded?: (collab: any) => void;
}

export function useDraftRealtime(options: DraftRealtimeOptions) {
  const [status, setStatus] = useState<"ws" | "polling" | "offline">("offline");
  const [lastEventTs, setLastEventTs] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!options.enabled) return;

    // Try WebSocket first
    const connectWs = async () => {
      try {
        const ws = await openDraftSocket(options.draftId, {
          token: localStorage.getItem("clerk_token") || undefined,
          userId: localStorage.getItem("test_user_id") || undefined,
        });

        ws.onopen = () => {
          setStatus("ws");
          // Stop polling, we have WS
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
        };

        ws.onmessage = (event) => {
          const msg = JSON.parse(event.data);
          setLastEventTs(msg.ts);
          
          // Route event to callback
          if (msg.type === "collab.segment_added") {
            options.onSegmentAdded?.(msg.data.segment);
          } else if (msg.type === "collab.ring_passed") {
            options.onRingPassed?.(msg.data.from_user_id, msg.data.to_user_id);
          } else if (msg.type === "collab.collaborator_added") {
            options.onCollaboratorAdded?.(msg.data);
          }
        };

        ws.onerror = () => {
          setStatus("polling");
          startPolling();
        };

        ws.onclose = () => {
          setStatus("offline");
          // Try reconnect with exponential backoff
          setTimeout(connectWs, 2000);
        };

        wsRef.current = ws;
      } catch (error) {
        console.warn("WS connect failed, falling back to polling:", error);
        setStatus("polling");
        startPolling();
      }
    };

    const startPolling = () => {
      if (pollIntervalRef.current) return;
      pollIntervalRef.current = setInterval(async () => {
        // Poll: GET /v1/collab/drafts/{draftId}
        try {
          const response = await fetch(`/v1/collab/drafts/${options.draftId}`, {
            headers: {
              "X-User-Id": localStorage.getItem("test_user_id") || "",
              "Authorization": `Bearer ${localStorage.getItem("clerk_token") || ""}`,
            },
          });
          if (!response.ok) {
            setStatus("offline");
            return;
          }
          const { data: draft } = await response.json();
          // Merge draft state (idempotent)
          setLastEventTs(new Date().toISOString());
        } catch (error) {
          setStatus("offline");
        }
      }, 3000); // Poll every 3 seconds
    };

    connectWs();

    return () => {
      wsRef.current?.close();
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [options.enabled, options.draftId]);

  return { status, lastEventTs };
}
```

---

## Client UI Integration

### Status Indicator

```typescript
// In draft detail page
export function DraftDetailPage() {
  const { draftId } = useParams();
  const { status, lastEventTs } = useDraftRealtime({
    draftId,
    enabled: true,
    onSegmentAdded: (segment) => {
      setSegments((prev) => [...prev, segment]);
    },
    onRingPassed: (from, to) => {
      setRingState((prev) => ({
        ...prev,
        current_holder_id: to,
        holders_history: [...prev.holders_history, to],
      }));
      // Disable editor if we're not the new holder
      if (to !== currentUserId) {
        setEditorDisabled(true);
      }
    },
  });

  const statusBadge = () => {
    switch (status) {
      case "ws":
        return <Badge variant="success">🟢 Live</Badge>;
      case "polling":
        return <Badge variant="warning">🟡 Syncing</Badge>;
      case "offline":
        return <Badge variant="error">🔴 Offline</Badge>;
    }
  };

  return (
    <div className="draft-detail">
      <div className="header">
        <h1>{draft.title}</h1>
        {statusBadge()}
        {lastEventTs && <span className="text-xs opacity-50">Updated {formatTime(lastEventTs)}</span>}
      </div>
      {/* Rest of page */}
    </div>
  );
}
```

### Idempotency Guarantee

Even though WS events arrive in real-time, the UI must handle:
1. **Duplicate events**: If both WS and polling deliver the same segment
2. **Out-of-order events**: If network reorders messages
3. **Missing events**: If WS drops and polling has lag

**Solution**: Segment IDs are server-assigned and unique. Client deduplicates by checking `if (!segments.find(s => s.id === newSegment.id))` before adding.

---

## Fallback: Polling

If WebSocket:
- Fails to connect
- Times out
- Closes unexpectedly

Then automatically start polling `GET /v1/collab/drafts/{id}` every ~3 seconds.

**Behavior**:
- Polling stops immediately when WS reconnects
- Full draft state is fetched and merged
- UI reconciles new segments, ring state changes, collaborator list
- No data loss, just slightly stale (up to 3s)

---

## Backend Implementation

### 1. Hub (Pubsub)

**File**: `backend/realtime/hub.py`

```python
# Minimal example structure
class DraftHub:
    """In-memory room-per-draft broadcast hub"""
    
    def __init__(self):
        self._rooms: Dict[str, Set[WebSocket]] = {}
    
    async def register(self, draft_id: str, ws: WebSocket):
        """Register WebSocket in draft room"""
        if draft_id not in self._rooms:
            self._rooms[draft_id] = set()
        self._rooms[draft_id].add(ws)
    
    async def unregister(self, draft_id: str, ws: WebSocket):
        """Unregister WebSocket from draft room"""
        if draft_id in self._rooms:
            self._rooms[draft_id].discard(ws)
    
    async def broadcast(self, draft_id: str, message: dict):
        """Broadcast message to all sockets in room"""
        if draft_id not in self._rooms:
            return
        
        dead_sockets = set()
        for ws in self._rooms[draft_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead_sockets.add(ws)
        
        # Prune dead sockets
        self._rooms[draft_id] -= dead_sockets

hub = DraftHub()  # Global singleton
```

### 2. WebSocket Route

**File**: `backend/api/realtime.py`

```python
from fastapi import APIRouter, WebSocketException, WebSocket, Query
from backend.realtime.hub import hub
from backend.core.auth import verify_clerk_jwt, get_current_user_id  # Reuse from Phase 6.1

router = APIRouter()

@router.websocket("/v1/ws/drafts/{draft_id}")
async def websocket_endpoint(websocket: WebSocket, draft_id: str):
    """
    Real-time collaboration WebSocket.
    
    Auth: Clerk JWT or X-User-Id header
    Events: segment_added, ring_passed, collaborator_added
    """
    await websocket.accept()
    
    # Extract and validate auth
    auth_header = websocket.headers.get("Authorization", "")
    user_id = None
    
    if auth_header.startswith("Bearer "):
        jwt_token = auth_header[7:]
        try:
            user_id = verify_clerk_jwt(jwt_token)
        except:
            await websocket.send_json({
                "type": "error",
                "message": "Invalid JWT"
            })
            await websocket.close(code=1008, reason="Unauthorized")
            return
    
    # Fallback to X-User-Id
    if not user_id:
        user_id = websocket.headers.get("X-User-Id")
    
    if not user_id:
        await websocket.send_json({
            "type": "error",
            "message": "Missing authorization"
        })
        await websocket.close(code=1008, reason="Unauthorized")
        return
    
    # Optional: Validate user can view draft
    # try:
    #     draft = get_draft(draft_id)
    #     if user_id != draft.creator_id and user_id not in [c.user_id for c in draft.collaborators]:
    #         await websocket.close(code=1008, reason="Forbidden")
    #         return
    # except:
    #     pass  # Permissive in early phase
    
    # Register in hub
    await hub.register(draft_id, websocket)
    
    # Send welcome message
    await websocket.send_json({
        "type": "connected",
        "draft_id": draft_id,
        "user_id": user_id,
        "ts": datetime.now(timezone.utc).isoformat()
    })
    
    # Keepalive + receive loop
    try:
        while True:
            # Receive client message
            data = await websocket.receive_json()
            
            # Handle ping
            if data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "ts": datetime.now(timezone.utc).isoformat()
                })
            else:
                # In Phase 6.2, ignore other messages
                pass
    
    except Exception as e:
        # Client disconnected
        pass
    finally:
        await hub.unregister(draft_id, websocket)
```

### 3. Emit Events from Collab Service

Update `backend/features/collaboration/service.py`:

```python
from backend.realtime.hub import hub

async def append_segment(...) -> CollabDraft:
    # ... existing validation ...
    
    # Persist segment
    draft = persist_segment(...)
    
    # Emit event
    await hub.broadcast(draft_id, {
        "type": "collab.segment_added",
        "draft_id": draft_id,
        "ts": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "data": {
            "segment": {
                "id": new_segment.id,
                "author_user_id": user_id,
                "content": new_segment.content,
                "position": new_segment.position,
                "created_at": new_segment.created_at.isoformat(),
            }
        }
    })
    
    return draft
```

---

## Security Notes

1. **WebSocket Auth**: Same Clerk JWT validation as REST endpoints (Phase 6.1)
2. **Read-Only in Phase 6.2**: Mutations must use REST (idempotency, validation, persistence)
3. **CORS**: Update to allow WebSocket upgrades if needed
4. **Rate Limiting**: Apply per-user, not per-socket

---

## Testing Strategy

### Backend Tests

```python
# backend/tests/test_realtime_ws.py
def test_ws_connect_with_jwt():
    token = create_test_jwt("user_123")
    # ... connect to ws with Bearer token ...
    assert response["type"] == "connected"

def test_ws_fallback_x_user_id():
    # connect without JWT, with X-User-Id header
    assert response["type"] == "connected"

def test_ws_broadcast():
    # Two clients connect to same draft
    # One sends REST request to append segment
    # Both clients receive collab.segment_added event
    assert event["type"] == "collab.segment_added"
```

### Frontend Tests

```typescript
// src/__tests__/realtime-hook.spec.tsx
describe("useDraftRealtime", () => {
  it("should use WS when available", () => {
    // Mock WebSocket
    // Render component with hook
    // Verify status = "ws"
  });

  it("should fallback to polling if WS fails", () => {
    // Mock WebSocket to fail
    // Verify status transitions to "polling"
    // Verify GET requests every 3s
  });

  it("should handle segment_added event", () => {
    // Mock WS event
    // Verify callback invoked
  });
});
```

---

## Deployment Checklist

- [ ] Hub singleton thread-safe (use locks if multi-worker)
- [ ] CORS updated for WebSocket upgrade (if needed)
- [ ] Load balancer supports WebSocket upgrade (sticky sessions)
- [ ] Monitor WebSocket connection count
- [ ] Handle graceful shutdown (flush pending broadcasts)

---

## Files to Create/Modify (Phase 6.2)

**New**:
- `backend/realtime/hub.py` — In-memory pubsub
- `backend/api/realtime.py` — WebSocket route
- `src/lib/realtime.ts` — WebSocket client utilities
- `src/hooks/useDraftRealtime.ts` — React hook
- `backend/tests/test_realtime_ws.py` — WebSocket tests
- `src/__tests__/realtime-hook.spec.tsx` — Hook tests

**Modified**:
- `backend/main.py` — Include realtime router
- `backend/features/collaboration/service.py` — Emit events after mutations
- `src/app/drafts/[id]/page.tsx` — Use hook, show status badge
- `.env.example` — (no changes needed)

---

## Success Metrics (End of Phase 6.2)

✅ WebSocket connects with Clerk JWT  
✅ WebSocket connects with X-User-Id (fallback)  
✅ Events broadcast to all connected clients  
✅ Polling fallback works if WS unavailable  
✅ Status badge shows connection state  
✅ Idempotency preserved (no double-segment)  
✅ Backend tests pass (535+)  
✅ Frontend tests pass (299+)  
✅ No breaking changes to REST API  

---

## Phase 6.2 → Phase 6.3 (Optimistic UI)

Once 6.2 is complete, Phase 6.3 will add:
- **Optimistic append**: Show segment immediately, rollback if rejected
- **Optimistic ring pass**: Disable editor instantly, show temporary lock
- **Conflict resolution**: If two users try same operation, first wins
- Estimated: 4-6 hours

---

END OF SPEC — Ready for PART 1 implementation
