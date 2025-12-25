/**
 * AnalyticsPanel - Phase 8.6 "Analytics Expansion"
 * 
 * Display segment-level metrics, contributor breakdown, and ring dynamics:
 * - Summary: Total segments/words, unique contributors, inactivity risk, avg hold time
 * - Contributors: Per-user metrics (segments, words, ring holds, wait suggestions)
 * - Ring: Current holder, holds history, passes, recommended next holder
 * 
 * Read-only for all collaborators (no mutations).
 */

"use client";

import React, { useState, useEffect } from "react";
import {
  DraftAnalyticsSummary,
  DraftAnalyticsContributors,
  DraftAnalyticsRing,
  DraftAnalyticsDaily,
  ContributorMetrics,
  RingHold,
  RingPass,
  InactivityRisk,
} from "@/types/collab";
import {
  getDraftAnalyticsSummary,
  getDraftAnalyticsContributors,
  getDraftAnalyticsRing,
  getDraftAnalyticsDaily,
} from "@/lib/collabApi";

interface AnalyticsPanelProps {
  draftId: string;
  isCollaborator: boolean; // Only collaborators can view analytics
}

type Tab = "summary" | "contributors" | "ring";

const INACTIVITY_RISK_COLORS: Record<InactivityRisk, string> = {
  low: "bg-green-100 text-green-800",
  medium: "bg-yellow-100 text-yellow-800",
  high: "bg-red-100 text-red-800",
};

function formatSeconds(seconds: number): string {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

function formatDate(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

export default function AnalyticsPanel({ draftId, isCollaborator }: AnalyticsPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("summary");
  
  // Summary tab
  const [summary, setSummary] = useState<DraftAnalyticsSummary | null>(null);
  
  // Contributors tab
  const [contributors, setContributors] = useState<DraftAnalyticsContributors | null>(null);
  
  // Ring tab
  const [ring, setRing] = useState<DraftAnalyticsRing | null>(null);
  
  // Daily activity
  const [daily, setDaily] = useState<DraftAnalyticsDaily | null>(null);
  const [dailyDays, setDailyDays] = useState(14);
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, [draftId, activeTab]);

  useEffect(() => {
    if (activeTab === "summary") loadDaily();
  }, [dailyDays]);

  async function loadData() {
    if (!isCollaborator) {
      setError("You must be a collaborator to view analytics");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      if (activeTab === "summary") {
        const data = await getDraftAnalyticsSummary(draftId);
        setSummary(data);
      } else if (activeTab === "contributors") {
        const data = await getDraftAnalyticsContributors(draftId);
        setContributors(data);
      } else if (activeTab === "ring") {
        const data = await getDraftAnalyticsRing(draftId);
        setRing(data);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }

  async function loadDaily() {
    try {
      const data = await getDraftAnalyticsDaily(draftId, dailyDays);
      setDaily(data);
    } catch (err: any) {
      console.error("Failed to load daily activity:", err);
    }
  }

  // ===== SUMMARY TAB =====

  function renderSummaryTab() {
    if (!summary) return <div className="p-4 text-gray-500">No data</div>;

    const riskColor = INACTIVITY_RISK_COLORS[summary.inactivity_risk];

    return (
      <div className="p-4 space-y-6">
        {/* Inactivity Risk Badge */}
        <div className="flex items-center justify-between bg-gray-50 p-4 rounded-lg">
          <div>
            <p className="text-sm font-medium text-gray-700">Inactivity Risk</p>
            <p className="text-xs text-gray-600 mt-1">
              {summary.hours_since_last_activity}h since last activity
            </p>
          </div>
          <span className={`px-3 py-1 rounded-full text-sm font-medium capitalize ${riskColor}`}>
            {summary.inactivity_risk}
          </span>
        </div>

        {/* Key Metrics Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600">Total Segments</p>
            <p className="text-2xl font-bold text-blue-600">{summary.total_segments}</p>
          </div>
          <div className="bg-purple-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600">Total Words</p>
            <p className="text-2xl font-bold text-purple-600">{summary.total_words}</p>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600">Contributors</p>
            <p className="text-2xl font-bold text-green-600">{summary.unique_contributors}</p>
          </div>
          <div className="bg-indigo-50 p-4 rounded-lg">
            <p className="text-sm text-gray-600">Avg Hold Time</p>
            <p className="text-lg font-bold text-indigo-600">
              {formatSeconds(summary.avg_time_holding_ring_seconds)}
            </p>
          </div>
        </div>

        {/* Daily Activity Chart (simplified) */}
        {daily && (
          <div className="mt-6 border-t pt-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-700">Daily Activity (last {dailyDays} days)</h3>
              <select
                value={dailyDays}
                onChange={(e) => setDailyDays(parseInt(e.target.value))}
                className="text-xs px-2 py-1 border rounded"
              >
                <option value={7}>7 days</option>
                <option value={14}>14 days</option>
                <option value={30}>30 days</option>
              </select>
            </div>
            <div className="space-y-2">
              {daily.daily.slice(0, 5).map((day) => (
                <div key={day.date} className="flex items-center gap-3">
                  <div className="w-20 text-xs text-gray-600">{new Date(day.date).toLocaleDateString()}</div>
                  <div className="flex-1 bg-gray-200 rounded h-5">
                    <div
                      className="bg-blue-500 h-full rounded"
                      style={{
                        width: `${Math.min(100, (day.segments_added + day.ring_passes * 2) * 10)}%`,
                      }}
                    />
                  </div>
                  <div className="w-16 text-xs text-gray-600 text-right">
                    +{day.segments_added}seg, {day.ring_passes}pass
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ===== CONTRIBUTORS TAB =====

  function renderContributorsTab() {
    if (!contributors) return <div className="p-4 text-gray-500">No data</div>;

    return (
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-100 border-b">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Contributor</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Segments</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Words</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Ring Holds</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Last Active</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {contributors.contributors.map((contributor) => (
              <tr key={contributor.user_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{contributor.user_id}</td>
                <td className="px-4 py-3 text-right text-gray-600">{contributor.segments_count}</td>
                <td className="px-4 py-3 text-right text-gray-600">{contributor.words_count}</td>
                <td className="px-4 py-3 text-right text-gray-600">{contributor.ring_holds_count}</td>
                <td className="px-4 py-3 text-right text-gray-600 text-xs">
                  {contributor.last_contribution_at
                    ? formatDate(contributor.last_contribution_at)
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  // ===== RING TAB =====

  function renderRingTab() {
    if (!ring) return <div className="p-4 text-gray-500">No data</div>;

    return (
      <div className="p-4 space-y-6">
        {/* Current Ring Holder */}
        {ring.holds.length > 0 && (
          <div className="bg-amber-50 border-l-4 border-amber-500 p-4">
            <p className="text-xs font-medium text-amber-700 uppercase">Currently Holding the Ring</p>
            <p className="text-lg font-bold text-amber-900 mt-2">{ring.holds[0].holder_id}</p>
            <p className="text-xs text-amber-700 mt-1">
              Held for {formatSeconds(ring.holds[0].hold_duration_seconds)}
            </p>
          </div>
        )}

        {/* Next Recommended Holder */}
        {ring.recommendation && (
          <div className="bg-blue-50 border border-blue-200 p-4 rounded-lg">
            <p className="text-sm font-medium text-blue-900">Recommended Next Holder</p>
            <p className="text-lg font-bold text-blue-600 mt-2">{ring.recommendation.recommended_user_id}</p>
            <p className="text-xs text-blue-700 mt-1">{ring.recommendation.reasoning}</p>
          </div>
        )}

        {/* Ring Holds History */}
        {ring.holds.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-700 mb-3">Ring Hold History</h3>
            <div className="space-y-2">
              {ring.holds.slice(0, 10).map((hold, idx) => (
                <div key={idx} className="flex items-center justify-between bg-gray-50 p-3 rounded">
                  <div>
                    <p className="font-medium text-gray-900">{hold.holder_id}</p>
                    <p className="text-xs text-gray-600">
                      {hold.start_at ? formatDate(hold.start_at) : "—"} to{" "}
                      {hold.end_at ? formatDate(hold.end_at) : "Present"}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-medium text-gray-900">{formatSeconds(hold.hold_duration_seconds)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Ring Passes History */}
        {ring.passes && ring.passes.length > 0 && (
          <div className="border-t pt-6">
            <h3 className="text-sm font-medium text-gray-700 mb-3">Last {Math.min(5, ring.passes.length)} Passes</h3>
            <div className="space-y-2">
              {ring.passes.slice(0, 5).map((pass, idx) => (
                <div key={idx} className="flex items-center justify-between bg-gray-50 p-3 rounded text-xs">
                  <p className="text-gray-700">
                    {pass.passed_by_id} → {pass.passed_to_id}
                  </p>
                  <p className="text-gray-600">{pass.passed_at ? formatDate(pass.passed_at) : "—"}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  // ===== MAIN RENDER =====

  if (!isCollaborator) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 p-4 rounded-lg">
        <p className="text-sm text-yellow-800">You must be a collaborator to view draft analytics.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
      {/* Tabs */}
      <div className="flex gap-0 border-b">
        {(["summary", "contributors", "ring"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? "border-blue-500 text-blue-600 bg-blue-50"
                : "border-transparent text-gray-700 hover:text-gray-900"
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="relative min-h-[400px]">
        {error && (
          <div className="p-4 bg-red-50 border-b border-red-200">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="p-8 flex items-center justify-center">
            <div className="text-center">
              <div className="animate-spin w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full mx-auto mb-3" />
              <p className="text-sm text-gray-600">Loading analytics...</p>
            </div>
          </div>
        ) : (
          <>
            {activeTab === "summary" && renderSummaryTab()}
            {activeTab === "contributors" && renderContributorsTab()}
            {activeTab === "ring" && renderRingTab()}
          </>
        )}
      </div>
    </div>
  );
}
