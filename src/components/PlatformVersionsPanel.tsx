"use client";

/**
 * PlatformVersionsPanel — Display and interact with platform-specific formatted outputs.
 * 
 * Phase 8.2: Auto-Format for Platform feature.
 * 
 * Features:
 * - Tabbed interface (X, YouTube, Instagram, Blog)
 * - Renders formatted blocks with platform-specific styling
 * - Copy to clipboard for each block
 * - Export as .txt, .md, or .csv
 * - Options panel for tone/hashtags/CTA customization
 */

import React, { useState, useCallback } from "react";
import { FormatPlatform, PlatformOutput, FormatOptions, FormatGenerateResponse } from "@/types/collab";
import { formatGenerate } from "@/lib/collabApi";

interface PlatformVersionsPanelProps {
  draftId: string;
  isAuthenticated: boolean;
  onError?: (message: string) => void;
}

export default function PlatformVersionsPanel({
  draftId,
  isAuthenticated,
  onError,
}: PlatformVersionsPanelProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<FormatGenerateResponse | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<FormatPlatform>("x");
  const [showOptions, setShowOptions] = useState(false);
  const [options, setOptions] = useState<FormatOptions>({
    tone: undefined,
    include_hashtags: true,
    include_cta: true,
  });
  const [copiedBlock, setCopiedBlock] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    if (!isAuthenticated) {
      onError?.("You must be signed in to format content.");
      return;
    }

    setLoading(true);
    try {
      const response = await formatGenerate({
        draft_id: draftId,
        platforms: undefined, // null = all platforms
        options: Object.values(options).some(v => v !== undefined) ? options : undefined,
      });
      setResult(response);
    } catch (error: any) {
      const message = error.message || "Failed to format content";
      onError?.(message);
      console.error("[PlatformVersionsPanel] error:", error);
    } finally {
      setLoading(false);
    }
  }, [draftId, isAuthenticated, options, onError]);

  const handleCopyBlock = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedBlock(text);
      setTimeout(() => setCopiedBlock(null), 2000);
    } catch (error) {
      console.error("[PlatformVersionsPanel] copy failed:", error);
    }
  }, []);

  const handleExport = useCallback((format: "txt" | "md" | "csv") => {
    if (!result) return;

    const output = result.outputs[selectedPlatform];
    if (!output) return;

    let content = "";
    const filename = `${draftId}-${selectedPlatform}.${format === "txt" ? "txt" : format === "md" ? "md" : "csv"}`;

    if (format === "txt") {
      content = output.plain_text;
    } else if (format === "md") {
      content = output.blocks
        .map(b => {
          if (b.type === "heading") return `## ${b.text}`;
          if (b.type === "hashtag") return `${b.text}`;
          if (b.type === "cta") return `> ${b.text}`;
          return b.text;
        })
        .join("\n\n");
    } else if (format === "csv") {
      content = "Type,Text\n" + output.blocks
        .map(b => `"${b.type}","${b.text.replace(/"/g, '""')}"`)
        .join("\n");
    }

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [result, selectedPlatform, draftId]);

  const output = result?.outputs[selectedPlatform];

  return (
    <div className="border rounded-lg p-6 bg-white">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Platform Versions</h3>
        <button
          onClick={handleGenerate}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? "Generating..." : "Generate All Platforms"}
        </button>
      </div>

      {/* Options Panel */}
      <div className="mb-4">
        <button
          onClick={() => setShowOptions(!showOptions)}
          className="text-sm text-blue-600 hover:underline"
        >
          {showOptions ? "Hide" : "Show"} Formatting Options
        </button>
        {showOptions && (
          <div className="mt-2 p-4 bg-gray-50 rounded space-y-3">
            <div>
              <label className="block text-sm font-medium mb-1">Tone</label>
              <select
                value={options.tone || ""}
                onChange={(e) => setOptions({ ...options, tone: (e.target.value as any) || undefined })}
                className="w-full px-3 py-2 border rounded"
              >
                <option value="">Default (None)</option>
                <option value="professional">Professional</option>
                <option value="casual">Casual</option>
                <option value="witty">Witty</option>
                <option value="motivational">Motivational</option>
                <option value="technical">Technical</option>
              </select>
            </div>

            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={options.include_hashtags}
                  onChange={(e) => setOptions({ ...options, include_hashtags: e.target.checked })}
                />
                <span className="text-sm">Include Hashtags</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={options.include_cta}
                  onChange={(e) => setOptions({ ...options, include_cta: e.target.checked })}
                />
                <span className="text-sm">Include CTA</span>
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Max Hashtags</label>
              <input
                type="number"
                min="0"
                max="30"
                value={options.hashtag_count || ""}
                onChange={(e) => setOptions({ ...options, hashtag_count: e.target.value ? parseInt(e.target.value) : undefined })}
                className="w-full px-3 py-2 border rounded"
                placeholder="No limit"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Custom CTA</label>
              <input
                type="text"
                value={options.cta_text || ""}
                onChange={(e) => setOptions({ ...options, cta_text: e.target.value || undefined })}
                className="w-full px-3 py-2 border rounded"
                placeholder="e.g., Join my community"
              />
            </div>
          </div>
        )}
      </div>

      {/* Tabs */}
      {result && (
        <>
          <div className="flex gap-2 mb-4 border-b">
            {(["x", "youtube", "instagram", "blog"] as FormatPlatform[]).map((platform) => (
              <button
                key={platform}
                onClick={() => setSelectedPlatform(platform)}
                className={`px-4 py-2 capitalize font-medium transition-colors ${
                  selectedPlatform === platform
                    ? "border-b-2 border-blue-600 text-blue-600"
                    : "text-gray-600 hover:text-gray-900"
                }`}
              >
                {platform === "x" ? "X (Twitter)" : platform.charAt(0).toUpperCase() + platform.slice(1)}
              </button>
            ))}
          </div>

          {/* Output Display */}
          {output && (
            <div className="space-y-4">
              {/* Metadata */}
              <div className="flex justify-between text-sm text-gray-600">
                <span>{output.block_count} blocks</span>
                <span>{output.character_count} characters</span>
              </div>

              {/* Warnings */}
              {output.warnings.length > 0 && (
                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded">
                  <p className="text-sm font-medium text-yellow-800 mb-1">Warnings:</p>
                  <ul className="list-disc list-inside text-sm text-yellow-700 space-y-1">
                    {output.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Blocks */}
              <div className="space-y-3">
                {output.blocks.map((block, i) => (
                  <div
                    key={i}
                    className={`p-3 rounded border-l-4 ${
                      block.type === "heading"
                        ? "border-l-purple-500 bg-purple-50"
                        : block.type === "hashtag"
                        ? "border-l-green-500 bg-green-50"
                        : block.type === "cta"
                        ? "border-l-blue-500 bg-blue-50"
                        : block.type === "media_note"
                        ? "border-l-gray-400 bg-gray-50"
                        : "border-l-gray-300 bg-gray-50"
                    }`}
                  >
                    <div className="flex justify-between items-start gap-2">
                      <div className="flex-1">
                        <p className="text-xs font-medium text-gray-600 mb-1 uppercase">{block.type}</p>
                        <p className="text-sm text-gray-900 whitespace-pre-wrap">{block.text}</p>
                      </div>
                      <button
                        onClick={() => handleCopyBlock(block.text)}
                        className="text-xs px-2 py-1 bg-white border rounded hover:bg-gray-100"
                      >
                        {copiedBlock === block.text ? "✓" : "Copy"}
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              {/* Plain Text */}
              <div className="p-3 bg-gray-100 rounded font-mono text-xs whitespace-pre-wrap break-words max-h-60 overflow-y-auto">
                {output.plain_text}
              </div>

              {/* Export Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => handleExport("txt")}
                  className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  Export TXT
                </button>
                <button
                  onClick={() => handleExport("md")}
                  className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  Export MD
                </button>
                <button
                  onClick={() => handleExport("csv")}
                  className="px-3 py-1 text-sm bg-gray-600 text-white rounded hover:bg-gray-700"
                >
                  Export CSV
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!result && !loading && (
        <p className="text-gray-500 text-center py-8">Click "Generate All Platforms" to see formatted outputs</p>
      )}
    </div>
  );
}
