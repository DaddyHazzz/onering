/**
 * Draft editor with ring-based edit locking.
 */

"use client";

import { useState } from "react";
import { CollabDraft } from "@/types/collab";

interface DraftEditorProps {
  draft: CollabDraft;
  isRingHolder: boolean;
  onAppendSegment: (content: string) => Promise<void>;
  isAppending: boolean;
}

export default function DraftEditor({
  draft,
  isRingHolder,
  onAppendSegment,
  isAppending,
}: DraftEditorProps) {
  const [content, setContent] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!content.trim()) {
      return;
    }

    try {
      await onAppendSegment(content);
      setContent(""); // Clear after successful append
    } catch (err) {
      // Error is handled by parent
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <h2 className="text-xl font-semibold text-white mb-4">Write Segment</h2>

      {!isRingHolder && (
        <div className="mb-4 p-3 bg-blue-500/20 border border-blue-500 rounded text-blue-300 text-sm">
          You don't hold the ring. The editor is read-only until you receive it.
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          maxLength={500}
          placeholder={isRingHolder ? "Write your segment..." : "Waiting for ring holder..."}
          disabled={!isRingHolder || isAppending}
          className={`w-full px-4 py-3 bg-slate-700 border border-slate-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition resize-none h-32 ${
            !isRingHolder ? "opacity-50 cursor-not-allowed" : ""
          }`}
        />

        <div className="flex items-center justify-between mt-3">
          <p className="text-xs text-gray-500">
            {content.length}/500 characters
          </p>
          <button
            type="submit"
            disabled={!isRingHolder || !content.trim() || isAppending}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isAppending ? "Appending..." : "Append Segment"}
          </button>
        </div>
      </form>
    </div>
  );
}
