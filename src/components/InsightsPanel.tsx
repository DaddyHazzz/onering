/**
 * Phase 8.7: Insights Panel
 * 
 * Displays actionable insights, recommendations, and alerts for a draft.
 * Replaces "holy shit this is cool" with "holy shit this thing actually helps me write better."
 * 
 * Features:
 * - Real-time insights (stalled, dominant user, low engagement, healthy)
 * - Actionable recommendations with one-click buttons (pass ring, invite user)
 * - Alerts (no activity, long hold, single contributor)
 * - Accessible keyboard navigation and screen reader support
 */

"use client";

import { useState, useEffect } from "react";
import { DraftInsightsResponse, DraftInsight, DraftRecommendation, DraftAlert } from "@/types/collab";
import { getDraftInsights } from "@/lib/collabApi";
import { passRing, addCollaborator } from "@/lib/collabApi";

interface InsightsPanelProps {
  draftId: string;
  currentUserId: string;
  onRefresh?: () => void;
}

export default function InsightsPanel({ draftId, currentUserId, onRefresh }: InsightsPanelProps) {
  const [insights, setInsights] = useState<DraftInsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const loadInsights = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getDraftInsights(draftId);
      setInsights(data);
    } catch (err: any) {
      setError(err.message || "Failed to load insights");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInsights();
  }, [draftId]);

  const handlePassRing = async (targetUserId: string) => {
    setActionLoading(`pass_ring_${targetUserId}`);
    try {
      await passRing(draftId, {
        to_user_id: targetUserId,
        idempotency_key: `pass_ring_${Date.now()}_${Math.random()}`
      });
      await loadInsights();
      onRefresh?.();
    } catch (err: any) {
      alert(err.message || "Failed to pass ring");
    } finally {
      setActionLoading(null);
    }
  };

  const handleInviteUser = async () => {
    const email = prompt("Enter email address to invite:");
    if (!email) return;
    
    setActionLoading("invite_user");
    try {
      // TODO: Wire up invite endpoint when ready
      alert(`Invite sent to ${email} (feature coming soon)`);
      await loadInsights();
      onRefresh?.();
    } catch (err: any) {
      alert(err.message || "Failed to invite user");
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="p-6 text-center" role="status" aria-live="polite">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
        <p className="mt-2 text-sm text-gray-600">Loading insights...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6" role="alert" aria-live="assertive">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-800">{error}</p>
          <button
            onClick={loadInsights}
            className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!insights) {
    return (
      <div className="p-6 text-center text-gray-500">
        <p>No insights available</p>
      </div>
    );
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "critical": return "text-red-600 bg-red-50 border-red-200";
      case "warning": return "text-yellow-600 bg-yellow-50 border-yellow-200";
      case "info": return "text-blue-600 bg-blue-50 border-blue-200";
      default: return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  const getAlertColor = (alertType: string) => {
    switch (alertType) {
      case "no_activity": return "text-red-600 bg-red-50 border-red-200";
      case "long_ring_hold": return "text-orange-600 bg-orange-50 border-orange-200";
      case "single_contributor": return "text-yellow-600 bg-yellow-50 border-yellow-200";
      default: return "text-gray-600 bg-gray-50 border-gray-200";
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">Draft Insights</h2>
        <button
          onClick={loadInsights}
          className="text-sm text-purple-600 hover:text-purple-800 underline"
          aria-label="Refresh insights"
        >
          Refresh
        </button>
      </div>

      {/* Insights Section */}
      {insights.insights.length > 0 && (
        <section aria-labelledby="insights-heading">
          <h3 id="insights-heading" className="text-lg font-semibold text-gray-900 mb-3">
            Insights
          </h3>
          <div className="space-y-3">
            {insights.insights.map((insight, idx) => (
              <div
                key={idx}
                className={`border rounded-lg p-4 ${getSeverityColor(insight.severity)}`}
                role="article"
                aria-labelledby={`insight-title-${idx}`}
              >
                <h4 id={`insight-title-${idx}`} className="font-semibold mb-1">
                  {insight.title}
                </h4>
                <p className="text-sm mb-2">{insight.message}</p>
                <details className="text-xs mt-2">
                  <summary className="cursor-pointer hover:underline">Why?</summary>
                  <p className="mt-1 pl-4">{insight.reason}</p>
                </details>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Recommendations Section */}
      {insights.recommendations.length > 0 && (
        <section aria-labelledby="recommendations-heading">
          <h3 id="recommendations-heading" className="text-lg font-semibold text-gray-900 mb-3">
            Recommendations
          </h3>
          <div className="space-y-3">
            {insights.recommendations.map((rec, idx) => (
              <div
                key={idx}
                className="bg-purple-50 border border-purple-200 rounded-lg p-4"
                role="article"
                aria-labelledby={`rec-title-${idx}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <h4 id={`rec-title-${idx}`} className="font-semibold text-purple-900 mb-1">
                      {getRecommendationTitle(rec.action)}
                    </h4>
                    <p className="text-sm text-purple-800 mb-2">{rec.reason}</p>
                    <p className="text-xs text-purple-600">
                      Confidence: {Math.round(rec.confidence * 100)}%
                    </p>
                  </div>
                  <div>
                    {rec.action === "pass_ring" && rec.target_user_id && (
                      <button
                        onClick={() => handlePassRing(rec.target_user_id!)}
                        disabled={actionLoading !== null}
                        className="px-3 py-1 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50"
                        aria-label={`Pass ring to ${rec.target_user_id}`}
                      >
                        {actionLoading === `pass_ring_${rec.target_user_id}` ? "Passing..." : "Pass Ring"}
                      </button>
                    )}
                    {rec.action === "invite_user" && (
                      <button
                        onClick={handleInviteUser}
                        disabled={actionLoading !== null}
                        className="px-3 py-1 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50"
                        aria-label="Invite user to collaborate"
                      >
                        {actionLoading === "invite_user" ? "Inviting..." : "Invite"}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Alerts Section */}
      {insights.alerts.length > 0 && (
        <section aria-labelledby="alerts-heading">
          <h3 id="alerts-heading" className="text-lg font-semibold text-gray-900 mb-3">
            Alerts
          </h3>
          <div className="space-y-3">
            {insights.alerts.map((alert, idx) => (
              <div
                key={idx}
                className={`border rounded-lg p-4 ${getAlertColor(alert.alert_type)}`}
                role="alert"
                aria-labelledby={`alert-title-${idx}`}
              >
                <h4 id={`alert-title-${idx}`} className="font-semibold mb-1">
                  {getAlertTitle(alert.alert_type)}
                </h4>
                <p className="text-sm mb-2">{alert.reason}</p>
                <div className="text-xs mt-2 space-y-1">
                  <p><strong>Threshold:</strong> {alert.threshold}</p>
                  <p><strong>Current:</strong> {JSON.stringify(alert.current_value)}</p>
                  <p><strong>Triggered:</strong> {new Date(alert.triggered_at).toLocaleString()}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Empty State */}
      {insights.insights.length === 0 && 
       insights.recommendations.length === 0 && 
       insights.alerts.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p className="text-lg">🎉 All good! No insights to report.</p>
          <p className="text-sm mt-2">Keep collaborating and we'll let you know if anything needs attention.</p>
        </div>
      )}

      {/* Timestamp */}
      <div className="text-xs text-gray-500 text-center border-t pt-4">
        Last updated: {new Date(insights.computed_at).toLocaleString()}
      </div>
    </div>
  );
}

function getRecommendationTitle(action: string): string {
  switch (action) {
    case "pass_ring": return "Pass the Ring";
    case "invite_user": return "Invite Collaborator";
    case "add_segment": return "Add Content";
    case "review_suggestions": return "Review Suggestions";
    default: return "Take Action";
  }
}

function getAlertTitle(alertType: string): string {
  switch (alertType) {
    case "no_activity": return "No Recent Activity";
    case "long_ring_hold": return "Ring Held Too Long";
    case "single_contributor": return "Solo Contributor";
    default: return "Alert";
  }
}
