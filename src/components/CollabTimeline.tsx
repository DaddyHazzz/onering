/**
 * CollabTimeline - Beautiful timeline view for draft history
 * Phase 8.3: Shows chronological events with icons and tooltips
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { TimelineEvent, TimelineResponse } from "@/types/collab";
import { getTimeline } from "@/lib/collabApi";

interface CollabTimelineProps {
  draftId: string;
  isAuthenticated: boolean;
  onError?: (message: string) => void;
}

export default function CollabTimeline({
  draftId,
  isAuthenticated,
  onError,
}: CollabTimelineProps) {
  const [loading, setLoading] = useState(false);
  const [timeline, setTimeline] = useState<TimelineResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadTimeline = useCallback(async () => {
    if (!isAuthenticated) {
      setError("Sign in to view timeline");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const result = await getTimeline(draftId, { limit: 50, asc: false });
      setTimeline(result);
    } catch (err: any) {
      const errorMsg = err?.message || "Failed to load timeline";
      setError(errorMsg);
      onError?.(errorMsg);
    } finally {
      setLoading(false);
    }
  }, [draftId, isAuthenticated, onError]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  const getEventIcon = (type: TimelineEvent["type"]) => {
    switch (type) {
      case "draft_created":
        return "✨";
      case "segment_added":
        return "🧑";
      case "ring_passed":
        return "👑";
      case "collaborator_added":
        return "➕";
      case "ai_suggested":
        return "🤖";
      case "format_generated":
        return "📋";
      default:
        return "📌";
    }
  };

  const formatRelativeTime = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  if (!isAuthenticated) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-6">
        <p className="text-sm text-gray-600">Sign in to view timeline</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-6">
        <p className="text-sm text-red-600">{error}</p>
        <button
          onClick={loadTimeline}
          className="mt-2 text-sm text-red-800 underline hover:no-underline"
        >
          Retry
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-6">
        <div className="flex items-center justify-center">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-blue-600 border-t-transparent"></div>
          <span className="ml-3 text-sm text-gray-600">Loading timeline...</span>
        </div>
      </div>
    );
  }

  if (!timeline || timeline.events.length === 0) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-6">
        <p className="text-sm text-gray-600">No events yet. Start collaborating!</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4">
        <h3 className="text-lg font-semibold text-gray-900">Timeline</h3>
        <button
          onClick={loadTimeline}
          disabled={loading}
          className="text-sm text-blue-600 hover:text-blue-800 disabled:text-gray-400"
        >
          Refresh
        </button>
      </div>

      <div className="max-h-[500px] overflow-y-auto p-6">
        <div className="space-y-4">
          {timeline.events.map((event) => (
            <div
              key={event.event_id}
              className="flex items-start space-x-3 rounded-lg border border-gray-100 p-3 hover:bg-gray-50"
              title={new Date(event.ts).toLocaleString()}
            >
              <div className="flex-shrink-0 text-2xl">
                {getEventIcon(event.type)}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-gray-900">{event.summary}</p>
                <p className="text-xs text-gray-500 mt-1">
                  {formatRelativeTime(event.ts)}
                </p>
                {event.meta && Object.keys(event.meta).length > 0 && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-blue-600 hover:text-blue-800">
                      Details
                    </summary>
                    <pre className="mt-1 text-xs text-gray-600 overflow-x-auto">
                      {JSON.stringify(event.meta, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            </div>
          ))}
        </div>

        {timeline.next_cursor && (
          <button
            onClick={async () => {
              if (!timeline.next_cursor) return;
              try {
                const more = await getTimeline(draftId, {
                  limit: 50,
                  asc: false,
                  cursor: timeline.next_cursor,
                });
                setTimeline({
                  ...timeline,
                  events: [...timeline.events, ...more.events],
                  next_cursor: more.next_cursor,
                });
              } catch (err: any) {
                onError?.(err?.message || "Failed to load more");
              }
            }}
            className="mt-4 w-full rounded-lg border border-blue-600 px-4 py-2 text-sm text-blue-600 hover:bg-blue-50"
          >
            Load More
          </button>
        )}
      </div>
    </div>
  );
}
