/**
 * Timeline of segments in a draft.
 */

"use client";

import { DraftSegment } from "@/types/collab";

interface SegmentTimelineProps {
  segments: DraftSegment[];
}

export default function SegmentTimeline({ segments }: SegmentTimelineProps) {
  if (segments.length === 0) {
    return (
      <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
        <h2 className="text-xl font-semibold text-white mb-4">Segments</h2>
        <p className="text-gray-400">No segments yet. Start by appending one!</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <h2 className="text-xl font-semibold text-white mb-4">
        Segments ({segments.length})
      </h2>

      <div className="space-y-4">
        {segments.map((segment, index) => (
          <div
            key={segment.segment_id}
            className="p-4 bg-slate-700 rounded-lg border border-slate-600"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-blue-400">
                  #{index + 1}
                </span>
                <span className="text-sm text-gray-400">
                  by <span className="text-gray-300 font-medium">@{segment.author_display || segment.user_id}</span>
                </span>
              </div>
              <span className="text-xs text-gray-500">
                {new Date(segment.created_at).toLocaleDateString()} at{" "}
                {new Date(segment.created_at).toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            </div>

            <p className="text-gray-200 leading-relaxed whitespace-pre-wrap">
              {segment.content}
            </p>

            {segment.ring_holder_display_at_write && (
              <div className="mt-3 pt-3 border-t border-slate-600">
                <p className="text-xs text-gray-500">
                  Ring holder at write: <span className="text-gray-300">@{segment.ring_holder_display_at_write}</span>
                </p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
