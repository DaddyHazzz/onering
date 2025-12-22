/**
 * src/components/analytics/DraftAnalyticsModal.tsx
 * Phase 3.4 draft analytics modal UI
 * Shows momentum snapshot for individual drafts
 */

"use client";

import { useState, useEffect } from "react";
import { X } from "lucide-react";

interface DraftAnalyticsData {
  draft_id: string;
  views: number;
  shares: number;
  segments_count: number;
  contributors_count: number;
  ring_passes_count: number;
  last_activity_at: string | null;
  computed_at: string;
}

interface DraftAnalyticsModalProps {
  draftId: string;
  isOpen: boolean;
  onClose: () => void;
}

export default function DraftAnalyticsModal({
  draftId,
  isOpen,
  onClose,
}: DraftAnalyticsModalProps) {
  const [data, setData] = useState<DraftAnalyticsData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (isOpen && draftId) {
      fetchAnalytics();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, draftId]);

  const fetchAnalytics = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/collab/drafts/${draftId}/analytics`);
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to load analytics");
      }
      const json = await res.json();
      if (json.success && json.data) {
        setData(json.data);
      } else {
        throw new Error("Invalid response format");
      }
    } catch (err: any) {
      console.error("[DraftAnalyticsModal] error:", err);
      setError(err.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50">
      <div className="bg-white rounded-lg shadow-xl max-w-lg w-full p-6 relative">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600"
          aria-label="Close"
        >
          <X size={24} />
        </button>

        {/* Header */}
        <h2 className="text-2xl font-bold text-gray-800 mb-4">Momentum Snapshot</h2>

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            <p className="font-medium">Error</p>
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
            <span className="ml-3 text-gray-600">Loading analytics...</span>
          </div>
        )}

        {/* Analytics Data */}
        {!loading && data && (
          <div className="space-y-4">
            {/* Engagement Metrics */}
            <div className="bg-blue-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Engagement</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-2xl font-bold text-blue-600">{data.views}</p>
                  <p className="text-xs text-gray-600">Views</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-blue-600">{data.shares}</p>
                  <p className="text-xs text-gray-600">Shares</p>
                </div>
              </div>
            </div>

            {/* Collaboration Activity */}
            <div className="bg-green-50 rounded-lg p-4">
              <h3 className="text-sm font-semibold text-gray-700 mb-3">Collaboration Activity</h3>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-2xl font-bold text-green-600">{data.segments_count}</p>
                  <p className="text-xs text-gray-600">Segments</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-green-600">{data.contributors_count}</p>
                  <p className="text-xs text-gray-600">Contributors</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-green-600">{data.ring_passes_count}</p>
                  <p className="text-xs text-gray-600">RING Passes</p>
                </div>
              </div>
            </div>

            {/* Last Activity */}
            {data.last_activity_at && (
              <div className="text-sm text-gray-600">
                <p>
                  <span className="font-medium">Last activity:</span>{" "}
                  {new Date(data.last_activity_at).toLocaleString()}
                </p>
              </div>
            )}

            {/* Timestamp */}
            <p className="text-xs text-gray-400 text-right">
              Computed at: {new Date(data.computed_at).toLocaleString()}
            </p>
          </div>
        )}

        {/* Refresh Button */}
        {!loading && (
          <div className="mt-6 flex justify-end">
            <button
              onClick={fetchAnalytics}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Refresh
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
