/**
 * Ring controls: pass ring to collaborators.
 */

"use client";

import { useState } from "react";
import { CollabDraft } from "@/types/collab";

interface RingControlsProps {
  draft: CollabDraft;
  isRingHolder: boolean;
  onPassRing: (toUserId: string) => Promise<void>;
  isLoading: boolean;
}

export default function RingControls({
  draft,
  isRingHolder,
  onPassRing,
  isLoading,
}: RingControlsProps) {
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const recipients = [draft.creator_id, ...draft.collaborators].filter(
    (id) => id !== draft.ring_state.current_holder_id
  );

  const handlePassRing = async () => {
    if (!selectedUserId) {
      setError("Please select a user");
      return;
    }

    try {
      setError(null);
      await onPassRing(selectedUserId);
      setSelectedUserId("");
    } catch (err: any) {
      setError(err.message || "Failed to pass ring");
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <h3 className="text-lg font-semibold text-white mb-4">👑 Ring Control</h3>

      <div className="space-y-4">
        {/* Current holder */}
        <div className="p-3 bg-slate-700 rounded border border-yellow-500/50">
          <p className="text-xs text-gray-400">Current Holder</p>
          <p className="text-white font-semibold mt-1">
            @{draft.ring_state.current_holder_id}
          </p>
        </div>

        {/* Pass ring controls */}
        {isRingHolder ? (
          <div className="space-y-3">
            <label className="block">
              <p className="text-sm font-medium text-gray-300 mb-2">
                Pass to:
              </p>
              <select
                value={selectedUserId}
                onChange={(e) => {
                  setSelectedUserId(e.target.value);
                  setError(null);
                }}
                disabled={isLoading || recipients.length === 0}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:border-blue-500 transition disabled:opacity-50"
              >
                <option value="">-- Select user --</option>
                {recipients.map((userId) => (
                  <option key={userId} value={userId}>
                    @{userId}
                  </option>
                ))}
              </select>
            </label>

            {error && (
              <p className="text-sm text-red-400">{error}</p>
            )}

            <button
              onClick={handlePassRing}
              disabled={!selectedUserId || isLoading || recipients.length === 0}
              className="w-full px-4 py-2 bg-yellow-600 text-white rounded-lg hover:bg-yellow-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {isLoading ? "Passing..." : "Pass Ring"}
            </button>
          </div>
        ) : (
          <p className="text-sm text-gray-400 p-3 bg-slate-700 rounded">
            You don't hold the ring. Only the current holder can pass it.
          </p>
        )}

        {/* Ring history */}
        {draft.ring_state.holders_history.length > 0 && (
          <div className="pt-4 border-t border-slate-700">
            <p className="text-xs font-medium text-gray-400 mb-2">
              Ring History
            </p>
            <div className="space-y-1">
              {draft.ring_state.holders_history.map((holder, idx) => (
                <p key={idx} className="text-xs text-gray-500">
                  {idx + 1}. @{holder}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
