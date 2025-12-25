/**
 * ExportPanel - Export drafts as markdown or JSON with credits
 * Phase 8.3: Premium export functionality with attribution
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { AttributionResponse, ExportRequest } from "@/types/collab";
import { getAttribution, exportDraft } from "@/lib/collabApi";

interface ExportPanelProps {
  draftId: string;
  isAuthenticated: boolean;
  onError?: (message: string) => void;
}

export default function ExportPanel({
  draftId,
  isAuthenticated,
  onError,
}: ExportPanelProps) {
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [attribution, setAttribution] = useState<AttributionResponse | null>(null);
  const [includeCredits, setIncludeCredits] = useState(true);

  const loadAttribution = useCallback(async () => {
    if (!isAuthenticated) return;

    setLoading(true);
    try {
      const result = await getAttribution(draftId);
      setAttribution(result);
    } catch (err: any) {
      console.error("Failed to load attribution:", err);
    } finally {
      setLoading(false);
    }
  }, [draftId, isAuthenticated]);

  useEffect(() => {
    loadAttribution();
  }, [loadAttribution]);

  const handleExport = async (format: "markdown" | "json") => {
    if (!isAuthenticated) {
      onError?.("Sign in to export");
      return;
    }

    setExporting(true);
    try {
      const result = await exportDraft(draftId, {
        format,
        include_credits: includeCredits,
      });

      // Trigger file download
      const blob = new Blob([result.content], { type: result.content_type });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = result.filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err: any) {
      const errorMsg = err?.message || `Failed to export as ${format}`;
      onError?.(errorMsg);
    } finally {
      setExporting(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-6">
        <p className="text-sm text-gray-600">Sign in to export draft</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">Export Draft</h3>

      {/* Credits Summary */}
      {attribution && attribution.contributors.length > 0 && (
        <div className="mb-6 rounded-lg border border-blue-100 bg-blue-50 p-4">
          <h4 className="text-sm font-semibold text-blue-900 mb-2">
            Top Contributors
          </h4>
          <div className="space-y-1">
            {attribution.contributors.slice(0, 3).map((contributor) => (
              <div
                key={contributor.user_id}
                className="flex items-center justify-between text-sm"
              >
                <span className="text-blue-800">
                  @{contributor.user_id.slice(-6)}
                </span>
                <span className="text-blue-600">
                  {contributor.segment_count} segment{contributor.segment_count !== 1 ? "s" : ""}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Options */}
      <div className="mb-6">
        <label className="flex items-center space-x-2">
          <input
            type="checkbox"
            checked={includeCredits}
            onChange={(e) => setIncludeCredits(e.target.checked)}
            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
          />
          <span className="text-sm text-gray-700">Include credits section</span>
        </label>
      </div>

      {/* Export Buttons */}
      <div className="space-y-3">
        <button
          onClick={() => handleExport("markdown")}
          disabled={exporting}
          className="w-full rounded-lg border border-blue-600 bg-blue-600 px-4 py-3 text-white hover:bg-blue-700 disabled:bg-gray-300 disabled:border-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {exporting ? (
            <span className="flex items-center justify-center">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent mr-2"></div>
              Exporting...
            </span>
          ) : (
            <>
              <span className="text-lg mr-2">📄</span>
              Export as Markdown
            </>
          )}
        </button>

        <button
          onClick={() => handleExport("json")}
          disabled={exporting}
          className="w-full rounded-lg border border-gray-300 bg-white px-4 py-3 text-gray-700 hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors"
        >
          {exporting ? (
            <span className="flex items-center justify-center">
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-600 border-t-transparent mr-2"></div>
              Please wait...
            </span>
          ) : (
            <>
              <span className="text-lg mr-2">📦</span>
              Export as JSON
            </>
          )}
        </button>
      </div>

      <p className="mt-4 text-xs text-gray-500">
        Exports include all segments{includeCredits ? " and contributor credits" : ""}.
        {" "}Perfect for publishing or archiving.
      </p>
    </div>
  );
}
