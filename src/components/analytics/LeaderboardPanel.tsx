/**
 * src/components/analytics/LeaderboardPanel.tsx
 * Phase 3.4 leaderboard UI component
 * Displays top 10 contributors (supportive language only)
 */

"use client";

import { useState, useEffect } from "react";
import Image from "next/image";

type MetricType = "collaboration" | "momentum" | "consistency";

interface LeaderboardEntry {
  position: number;
  user_id: string;
  display_name: string;
  avatar_url: string | null;
  metric_value: number;
  metric_label: string;
  insight: string;
}

interface LeaderboardData {
  metric_type: MetricType;
  entries: LeaderboardEntry[];
  computed_at: string;
  message: string;
}

export default function LeaderboardPanel() {
  const [metric, setMetric] = useState<MetricType>("collaboration");
  const [data, setData] = useState<LeaderboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaderboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/analytics/leaderboard?metric=${metric}`);
      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.error || "Failed to load leaderboard");
      }
      const json = await res.json();
      if (json.success && json.data) {
        // Defensive: Cap at 10 entries even if API returns more
        const cappedEntries = json.data.entries.slice(0, 10);
        setData({ ...json.data, entries: cappedEntries });
      } else {
        throw new Error("Invalid response format");
      }
    } catch (err: any) {
      console.error("[LeaderboardPanel] error:", err);
      setError(err.message || "Failed to load leaderboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeaderboard();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [metric]);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-2xl font-bold text-gray-800">Community Highlights</h2>
        <button
          onClick={fetchLeaderboard}
          disabled={loading}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* Metric Selector */}
      <div className="mb-4">
        <label htmlFor="metric-select" className="block text-sm font-medium text-gray-700 mb-2">
          Highlight Type
        </label>
        <select
          id="metric-select"
          value={metric}
          onChange={(e) => setMetric(e.target.value as MetricType)}
          className="w-full px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="collaboration">Collaboration</option>
          <option value="momentum">Momentum</option>
          <option value="consistency">Consistency</option>
        </select>
      </div>

      {/* Message */}
      {data && (
        <p className="text-sm text-gray-600 mb-4 italic">{data.message}</p>
      )}

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
          <span className="ml-3 text-gray-600">Loading highlights...</span>
        </div>
      )}

      {/* Leaderboard Entries */}
      {!loading && data && data.entries.length > 0 && (
        <div className="space-y-3">
          {data.entries.map((entry) => (
            <div
              key={entry.user_id}
              className="flex items-center p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
            >
              {/* Position Badge */}
              <div className="flex-shrink-0 w-8 h-8 flex items-center justify-center bg-blue-500 text-white rounded-full font-bold text-sm mr-4">
                {entry.position}
              </div>

              {/* Avatar */}
              <div className="flex-shrink-0 mr-4">
                {entry.avatar_url ? (
                  <Image
                    src={entry.avatar_url}
                    alt={entry.display_name}
                    width={40}
                    height={40}
                    className="rounded-full"
                  />
                ) : (
                  <div className="w-10 h-10 bg-gray-300 rounded-full flex items-center justify-center text-gray-600 font-bold">
                    {entry.display_name.charAt(0).toUpperCase()}
                  </div>
                )}
              </div>

              {/* User Info */}
              <div className="flex-grow">
                <h3 className="font-semibold text-gray-800">{entry.display_name}</h3>
                <p className="text-sm text-gray-600">{entry.metric_label}</p>
                <p className="text-xs text-gray-500 italic mt-1">{entry.insight}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty State */}
      {!loading && data && data.entries.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <p className="text-lg font-medium">No highlights yet</p>
          <p className="text-sm">Start collaborating to see community activity</p>
        </div>
      )}

      {/* Timestamp */}
      {data && (
        <p className="text-xs text-gray-400 mt-4 text-right">
          Last updated: {new Date(data.computed_at).toLocaleString()}
        </p>
      )}
    </div>
  );
}
