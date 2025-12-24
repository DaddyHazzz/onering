/**
 * src/hooks/useDraftRealtime.ts
 * React hook for real-time draft synchronization.
 *
 * Phase 6.2: Manages WebSocket connection with fallback to polling.
 * Provides status updates and event callbacks.
 */

"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  openDraftSocket,
  parseEvent,
  RealtimeEvent,
  isSegmentAddedEvent,
  isRingPassedEvent,
  isCollaboratorAddedEvent,
  isDraftUpdatedEvent,
  isControlMessage,
} from "@/lib/realtime";

export type RealtimeStatus = "ws" | "polling" | "offline";

export interface DraftSegment {
  id: number | string;
  author_user_id: string;
  content: string;
  position: number;
  created_at: string;
}

export interface DraftRealtimeOptions {
  draftId: string;
  enabled?: boolean;
  onSegmentAdded?: (segment: DraftSegment) => void;
  onRingPassed?: (fromUserId: string, toUserId: string) => void;
  onCollaboratorAdded?: (collaboratorId: string) => void;
  onDraftUpdated?: (data: any) => void;
  onError?: (error: Error) => void;
}

export interface DraftRealtimeState {
  status: RealtimeStatus;
  lastEventTs: string | null;
  wsConnecting: boolean;
}

/**
 * Hook to manage real-time draft synchronization.
 *
 * Automatically tries WebSocket first, falls back to polling if unavailable.
 * Gracefully handles disconnections with exponential backoff retry.
 *
 * @param options Configuration
 * @returns State object with status and timestamp
 */
export function useDraftRealtime(
  options: DraftRealtimeOptions
): DraftRealtimeState {
  const {
    draftId,
    enabled = true,
    onSegmentAdded,
    onRingPassed,
    onCollaboratorAdded,
    onDraftUpdated,
    onError,
  } = options;

  const [status, setStatus] = useState<RealtimeStatus>("offline");
  const [lastEventTs, setLastEventTs] = useState<string | null>(null);
  const [wsConnecting, setWsConnecting] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const mountedRef = useRef(true);

  // Get auth headers (reuse from collabApi)
  const getAuthHeaders = useCallback(async () => {
    const clerkToken = typeof window !== "undefined" ? localStorage.getItem("clerk_token") : null;
    if (clerkToken) {
      return { Authorization: `Bearer ${clerkToken}` };
    }

    const testUserId = typeof window !== "undefined" ? localStorage.getItem("test_user_id") : null;
    if (testUserId) {
      return { "X-User-Id": testUserId };
    }

    return {};
  }, []);

  // Handle incoming event
  const handleEvent = useCallback(
    (event: RealtimeEvent) => {
      if (!mountedRef.current) return;

      setLastEventTs(event.ts);

      if (isSegmentAddedEvent(event) && event.data.segment) {
        onSegmentAdded?.(event.data.segment);
      } else if (isRingPassedEvent(event)) {
        onRingPassed?.(event.data.from_user_id, event.data.to_user_id);
      } else if (isCollaboratorAddedEvent(event)) {
        onCollaboratorAdded?.(event.data.collaborator_id);
      } else if (isDraftUpdatedEvent(event)) {
        onDraftUpdated?.(event.data);
      }
    },
    [onSegmentAdded, onRingPassed, onCollaboratorAdded, onDraftUpdated]
  );

  // Start polling fallback
  const startPolling = useCallback(() => {
    if (pollIntervalRef.current) return;

    if (!mountedRef.current) return;
    setStatus("polling");

    pollIntervalRef.current = setInterval(async () => {
      if (!mountedRef.current) return;

      try {
        const headers = await getAuthHeaders();
        const response = await fetch(`/v1/collab/drafts/${draftId}`, { headers });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const { data: draft } = await response.json();
        setLastEventTs(new Date().toISOString());
        // Note: Client should maintain last-known state and reconcile diffs
        // For Phase 6.2, we just update timestamp to indicate freshness
      } catch (error) {
        if (mountedRef.current) {
          setStatus("offline");
          onError?.(error instanceof Error ? error : new Error(String(error)));
        }
      }
    }, 3000);
  }, [draftId, getAuthHeaders, onError]);

  // Stop polling
  const stopPolling = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
  }, []);

  // Connect to WebSocket
  const connectWs = useCallback(async () => {
    if (!mountedRef.current || wsRef.current) return;

    if (wsConnecting) return;
    setWsConnecting(true);

    try {
      // Try to open WebSocket
      const ws = await openDraftSocket(draftId);

      if (!mountedRef.current) {
        ws.close();
        return;
      }

      wsRef.current = ws;
      reconnectAttemptsRef.current = 0;

      // Stop polling since we have WS
      stopPolling();
      if (!mountedRef.current) return;
      setStatus("ws");

      // Setup WebSocket handlers
      ws.onmessage = (event: MessageEvent) => {
        if (!mountedRef.current) return;

        try {
          const msg = parseEvent(event.data);

          // Skip control messages
          if (isControlMessage(msg)) {
            return;
          }

          // Handle actual events
          handleEvent(msg);
        } catch (error) {
          console.error("[realtime] Failed to parse message:", error);
        }
      };

      ws.onerror = (event: Event) => {
        console.error("[realtime] WebSocket error:", event);
        if (mountedRef.current) {
          setStatus("polling");
          startPolling();
        }
      };

      ws.onclose = (event: CloseEvent) => {
        if (!mountedRef.current) return;

        console.debug(
          "[realtime] WebSocket closed:",
          event.code,
          event.reason
        );
        wsRef.current = null;

        // Retry with exponential backoff
        if (reconnectAttemptsRef.current < 10) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
          reconnectAttemptsRef.current++;

          reconnectTimeoutRef.current = setTimeout(() => {
            if (mountedRef.current) {
              connectWs();
            }
          }, delay);
        } else {
          setStatus("offline");
          startPolling();
        }
      };

      // Send ping every 30 seconds to keep connection alive
      const pingInterval = setInterval(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          try {
            wsRef.current.send(JSON.stringify({ type: "ping" }));
          } catch (error) {
            console.debug("[realtime] Failed to send ping:", error);
          }
        } else {
          clearInterval(pingInterval);
        }
      }, 30000);
    } catch (error) {
      console.warn("[realtime] WebSocket connect failed, using polling:", error);
      if (mountedRef.current) {
        setStatus("polling");
        startPolling();
      }
    } finally {
      if (mountedRef.current) {
        setWsConnecting(false);
      }
    }
  }, [draftId, wsConnecting, stopPolling, startPolling, handleEvent]);

  // Setup and cleanup
  useEffect(() => {
    mountedRef.current = true;

    if (!enabled) {
      return () => {
        mountedRef.current = false;
      };
    }

    // Try WebSocket first
    connectWs();

    // Cleanup on unmount
    return () => {
      mountedRef.current = false;

      // Close WebSocket
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      // Stop polling
      stopPolling();

      // Clear reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [enabled, connectWs, stopPolling, draftId]);

  return {
    status,
    lastEventTs,
    wsConnecting,
  };
}
