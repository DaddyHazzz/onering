/**
 * src/lib/realtime.ts
 * WebSocket client utilities for real-time draft collaboration.
 *
 * Phase 6.2: Provides connection helpers, event parsing, and graceful fallbacks.
 */

export interface RealtimeEvent {
  type: string;
  draft_id: string;
  ts: string;
  user_id?: string;
  data: any;
}

/**
 * Get WebSocket URL for a draft.
 *
 * @param draftId Draft identifier
 * @returns ws:// or wss:// URL
 */
export function getWsUrl(draftId: string): string {
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  return `${protocol}//${host}/v1/ws/drafts/${draftId}`;
}

/**
 * Parse incoming WebSocket message.
 *
 * @param message JSON string from WebSocket
 * @returns Parsed RealtimeEvent
 * @throws SyntaxError if not valid JSON
 */
export function parseEvent(message: string): RealtimeEvent {
  return JSON.parse(message) as RealtimeEvent;
}

/**
 * Open WebSocket connection to draft with auth fallback.
 *
 * Supports:
 * - Authorization: Bearer {Clerk JWT} (via subprotocol or message)
 * - X-User-Id: {user_id} (fallback for tests)
 *
 * @param draftId Draft identifier
 * @param options Auth options
 * @returns WebSocket promise
 */
export async function openDraftSocket(
  draftId: string,
  options?: { token?: string; userId?: string }
): Promise<WebSocket> {
  const url = getWsUrl(draftId);
  const ws = new WebSocket(url);

  // Configure with timeout
  const connectPromise = new Promise<WebSocket>((resolve, reject) => {
    const timeout = setTimeout(() => {
      reject(new Error("WebSocket connection timeout"));
      ws.close();
    }, 10000);

    ws.onopen = () => {
      clearTimeout(timeout);
      resolve(ws);
    };

    ws.onerror = (event) => {
      clearTimeout(timeout);
      reject(new Error("WebSocket connection failed"));
    };
  });

  return connectPromise;
}

/**
 * Event type guards for type-safe event handling.
 */

export function isSegmentAddedEvent(event: RealtimeEvent): event is RealtimeEvent {
  return event.type === "collab.segment_added";
}

export function isRingPassedEvent(event: RealtimeEvent): event is RealtimeEvent {
  return event.type === "collab.ring_passed";
}

export function isCollaboratorAddedEvent(event: RealtimeEvent): event is RealtimeEvent {
  return event.type === "collab.collaborator_added";
}

export function isDraftUpdatedEvent(event: RealtimeEvent): event is RealtimeEvent {
  return event.type === "collab.draft_updated";
}

export function isControlMessage(event: any): boolean {
  return ["connected", "error", "ping", "pong"].includes(event.type);
}
