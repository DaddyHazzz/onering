"use client";

import { useEffect, useState } from "react";
import { CollabDraft } from "@/types/collab";
import { aiSuggest } from "@/lib/collabApi";

interface AISuggestionsPanelProps {
  draft: CollabDraft;
  isRingHolder: boolean;
  isAuthenticated: boolean;
  onInsertSegment: (content: string) => Promise<void>;
}

type SuggestionMode = "next" | "rewrite" | "summary" | "commentary";

export default function AISuggestionsPanel({
  draft,
  isRingHolder,
  isAuthenticated,
  onInsertSegment,
}: AISuggestionsPanelProps) {
  const [preview, setPreview] = useState<string>("");
  const [activeMode, setActiveMode] = useState<SuggestionMode | null>(null);
  const [loadingMode, setLoadingMode] = useState<SuggestionMode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [inserting, setInserting] = useState(false);

  const canRequest = isAuthenticated && (!loadingMode && !inserting);

  const fetchSuggestion = async (mode: SuggestionMode) => {
    if (!canRequest) return;
    setLoadingMode(mode);
    setError(null);
    try {
      const result = await aiSuggest(draft.draft_id, mode, draft.platform as any);
      setPreview(result.content || "");
      setActiveMode(result.mode as SuggestionMode);
    } catch (err: any) {
      setError(err?.message || "Failed to fetch AI suggestion");
      setPreview("");
      setActiveMode(null);
    } finally {
      setLoadingMode(null);
    }
  };

  const handleInsert = async () => {
    if (!preview || inserting) return;
    try {
      setInserting(true);
      await onInsertSegment(preview);
    } catch (err: any) {
      setError(err?.message || "Failed to insert segment");
    } finally {
      setInserting(false);
    }
  };

  useEffect(() => {
    // Auto-fetch commentary for non-holders once per draft load
    if (!isRingHolder && isAuthenticated && draft?.draft_id) {
      fetchSuggestion("commentary");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft?.draft_id, isRingHolder, isAuthenticated]);

  const holderButtons = (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
      <button
        onClick={() => fetchSuggestion("next")}
        disabled={!canRequest}
        className="px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
      >
        {loadingMode === "next" ? "Generating…" : "Suggest Next Segment"}
      </button>
      <button
        onClick={() => fetchSuggestion("rewrite")}
        disabled={!canRequest}
        className="px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
      >
        {loadingMode === "rewrite" ? "Rewriting…" : "Rewrite Previous"}
      </button>
      <button
        onClick={() => fetchSuggestion("summary")}
        disabled={!canRequest}
        className="px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
      >
        {loadingMode === "summary" ? "Summarizing…" : "Summarize So Far"}
      </button>
    </div>
  );

  const commentaryButton = (
    <button
      onClick={() => fetchSuggestion("commentary")}
      disabled={!canRequest}
      className="px-3 py-2 bg-slate-700 text-white rounded-lg border border-slate-600 hover:bg-slate-600 transition disabled:opacity-50"
    >
      {loadingMode === "commentary" ? "Thinking…" : "Refresh Commentary"}
    </button>
  );

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-400">AI Turn Suggestions</p>
          <h3 className="text-xl font-semibold text-white">Ring-aware assistant</h3>
        </div>
        <span className="text-sm text-yellow-300">
          {isRingHolder ? "👑 You hold the ring" : "Waiting for the ring"}
        </span>
      </div>

      {!isAuthenticated && (
        <div className="p-3 bg-slate-700 rounded text-slate-200 text-sm">
          Sign in to request AI suggestions.
        </div>
      )}

      {isRingHolder ? (
        holderButtons
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-slate-200">When you get the ring, you might add…</p>
          {commentaryButton}
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-500/20 border border-red-500 rounded text-red-200 text-sm">
          {error}
        </div>
      )}

      <div className="bg-slate-900 border border-slate-700 rounded p-4 min-h-[120px]">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm text-slate-300">{activeMode ? activeMode.toUpperCase() : "Preview"}</p>
          {preview && isRingHolder && (
            <button
              onClick={handleInsert}
              disabled={inserting}
              className="px-3 py-1 bg-emerald-600 text-white rounded hover:bg-emerald-700 transition disabled:opacity-50"
            >
              {inserting ? "Inserting…" : "Insert as Segment"}
            </button>
          )}
        </div>
        {preview ? (
          <p className="text-slate-100 whitespace-pre-wrap text-sm leading-relaxed">{preview}</p>
        ) : (
          <p className="text-slate-500 text-sm">No suggestion yet.</p>
        )}
      </div>
    </div>
  );
}
