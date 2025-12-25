/**
 * Phase 8.9: Insights Summary Card
 * 
 * Lightweight summary of draft insights for use in lists.
 * Shows highest-severity insight + alert/recommendation counts.
 * Designed for draft lists and dashboards.
 */

"use client";

import { useState, useEffect } from "react";
import { DraftInsightsResponse } from "@/types/collab";
import { getDraftInsights } from "@/lib/collabApi";

interface InsightsSummaryCardProps {
  draftId: string;
  compact?: boolean; // If true, show minimal version
}

export function InsightsSummaryCard({ draftId, compact = false }: InsightsSummaryCardProps) {
  const [insights, setInsights] = useState<DraftInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadInsights = async () => {
      try {
        setLoading(true);
        const data = await getDraftInsights(draftId);
        setInsights(data);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadInsights();
  }, [draftId]);

  if (loading) {
    return (
      <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
        <div className="h-4 bg-gray-200 rounded animate-pulse w-20"></div>
      </div>
    );
  }

  if (error || !insights) {
    return null; // Silently fail for list views
  }

  // Find highest-severity insight
  const severityOrder = { critical: 0, warning: 1, info: 2 };
  const topInsight = insights.insights.length > 0
    ? insights.insights.reduce((a, b) =>
        (severityOrder[a.severity as keyof typeof severityOrder] ??
          3) <
        (severityOrder[b.severity as keyof typeof severityOrder] ?? 3)
          ? a
          : b
      )
    : null;

  const alertCount = insights.alerts.length;
  const recommendationCount = insights.recommendations.length;

  if (compact) {
    return (
      <div className="text-xs text-gray-600">
        {alertCount > 0 && (
          <span className="inline-block mr-2 px-2 py-1 bg-red-50 border border-red-200 rounded text-red-700 font-medium">
            {alertCount} alert{alertCount !== 1 ? "s" : ""}
          </span>
        )}
        {recommendationCount > 0 && (
          <span className="inline-block px-2 py-1 bg-blue-50 border border-blue-200 rounded text-blue-700 font-medium">
            {recommendationCount} rec{recommendationCount !== 1 ? "s" : ""}
          </span>
        )}
        {alertCount === 0 && recommendationCount === 0 && (
          <span className="text-green-700">✓ All good</span>
        )}
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-gray-900 text-sm">Insights Summary</h4>
        <div className="flex gap-2">
          {alertCount > 0 && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
              {alertCount} Alert{alertCount !== 1 ? "s" : ""}
            </span>
          )}
          {recommendationCount > 0 && (
            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              {recommendationCount} Rec{recommendationCount !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      {/* Top Insight */}
      {topInsight && (
        <div
          className={`p-3 border-l-4 rounded text-sm ${
            topInsight.severity === "critical"
              ? "bg-red-50 border-red-300 text-red-800"
              : topInsight.severity === "warning"
                ? "bg-yellow-50 border-yellow-300 text-yellow-800"
                : "bg-blue-50 border-blue-300 text-blue-800"
          }`}
        >
          <p className="font-medium">{topInsight.title}</p>
          <p className="text-xs mt-1">{topInsight.message}</p>
        </div>
      )}

      {/* Empty State */}
      {!topInsight && alertCount === 0 && recommendationCount === 0 && (
        <div className="text-sm text-green-700 bg-green-50 p-3 border border-green-200 rounded">
          ✓ Healthy collaboration! No action needed.
        </div>
      )}

      {/* Timestamp */}
      <div className="text-xs text-gray-500 text-right">
        Updated {new Date(insights.computed_at).toLocaleTimeString()}
      </div>
    </div>
  );
}
