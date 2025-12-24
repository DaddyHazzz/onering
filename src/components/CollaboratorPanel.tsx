/**
 * Collaborator management panel.
 */

"use client";

import { useState } from "react";
import { CollabDraft } from "@/types/collab";

interface CollaboratorPanelProps {
  draft: CollabDraft;
  isCreator: boolean;
  onAddCollaborator: (collaboratorId: string) => Promise<void>;
  isLoading: boolean;
}

export default function CollaboratorPanel({
  draft,
  isCreator,
  onAddCollaborator,
  isLoading,
}: CollaboratorPanelProps) {
  const [newCollaboratorId, setNewCollaboratorId] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleAddCollaborator = async () => {
    if (!newCollaboratorId.trim()) {
      setError("Please enter a user ID");
      return;
    }

    try {
      setError(null);
      await onAddCollaborator(newCollaboratorId);
      setNewCollaboratorId("");
    } catch (err: any) {
      setError(err.message || "Failed to add collaborator");
    }
  };

  const allMembers = [draft.creator_id, ...draft.collaborators];

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
      <h3 className="text-lg font-semibold text-white mb-4">Collaborators</h3>

      <div className="space-y-4">
        {/* Collaborators list */}
        <div className="space-y-2">
          {allMembers.map((userId, idx) => (
            <div
              key={userId}
              className="p-3 bg-slate-700 rounded border border-slate-600 flex items-center justify-between"
            >
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-300">@{userId}</span>
                {idx === 0 && (
                  <span className="text-xs font-semibold text-blue-400 px-2 py-0.5 bg-blue-500/20 rounded">
                    Creator
                  </span>
                )}
                {draft.ring_state.current_holder_id === userId && (
                  <span className="text-xs font-semibold text-yellow-400">
                    👑
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Add collaborator */}
        {isCreator && (
          <div className="space-y-3 pt-4 border-t border-slate-700">
            <label className="block">
              <p className="text-sm font-medium text-gray-300 mb-2">
                Add Collaborator
              </p>
              <input
                type="text"
                value={newCollaboratorId}
                onChange={(e) => {
                  setNewCollaboratorId(e.target.value);
                  setError(null);
                }}
                placeholder="Enter user ID..."
                disabled={isLoading}
                className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition disabled:opacity-50"
              />
            </label>

            {error && (
              <p className="text-sm text-red-400">{error}</p>
            )}

            <button
              onClick={handleAddCollaborator}
              disabled={!newCollaboratorId.trim() || isLoading}
              className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed font-medium"
            >
              {isLoading ? "Adding..." : "Add"}
            </button>
          </div>
        )}

        {!isCreator && (
          <p className="text-xs text-gray-400 p-3 bg-slate-700 rounded">
            Only the creator can add collaborators.
          </p>
        )}
      </div>
    </div>
  );
}
