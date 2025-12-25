/**
 * Ring controls: pass ring to collaborators.
 */

"use client";

import { useState } from "react";
import { CollabDraft, SmartPassStrategy } from "@/types/collab";

interface RingControlsProps {
  draft: CollabDraft;
  isRingHolder: boolean;
  onPassRing: (toUserId: string) => Promise<void>;
  onSmartPass?: (strategy: SmartPassStrategy) => Promise<{ to_user_id: string; reason: string }>;
  isLoading: boolean;
}

export default function RingControls({
  draft,
  isRingHolder,
  onPassRing,
  onSmartPass,
  isLoading,
}: RingControlsProps) {
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [smartStrategy, setSmartStrategy] = useState<SmartPassStrategy>("most_inactive");
  const [smartReason, setSmartReason] = useState<string | null>(null);

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

  const handleSmartPass = async () => {
    if (!onSmartPass) return;
    try {
      setError(null);
      setSmartReason(null);
      const result = await onSmartPass(smartStrategy);
      setSmartReason(`Selected @${result.to_user_id} — ${result.reason}`);
      setSelectedUserId("");
    } catch (err: any) {
      setError(err.message || "Failed to smart pass ring");
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
            <label htmlFor="pass-select" className="block">
              <p className="text-sm font-medium text-gray-300 mb-2">
                Pass to:
              </p>
              <select
                id="pass-select"
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

            {/* Smart pass */}
            {onSmartPass && (
              <div className="mt-4 space-y-2 border-t border-slate-700 pt-4">
                <label htmlFor="smart-strategy" className="block">
                  <p className="text-sm font-medium text-gray-300 mb-2">Smart Pass Strategy</p>
                  <select
                    id="smart-strategy"
                    value={smartStrategy}
                    onChange={(e) => {
                      setSmartStrategy(e.target.value as SmartPassStrategy);
                      setSmartReason(null);
                      setError(null);
                    }}
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:border-blue-500 transition"
                  >
                    <option value="most_inactive">Most inactive</option>
                    <option value="round_robin">Round robin</option>
                    <option value="back_to_creator">Back to creator</option>
                  </select>
                </label>
                <button
                  onClick={handleSmartPass}
                  disabled={isLoading || recipients.length === 0}
                  className="w-full px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
                  aria-label="Smart pass ring"
                >
                  {isLoading ? "Passing..." : "Smart Pass"}
                </button>
                {smartReason && (
                  <p className="text-xs text-gray-400">{smartReason}</p>
                )}
              </div>
            )}
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
