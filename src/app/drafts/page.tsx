/**
 * Draft list page: /drafts
 * Shows all drafts the user is involved in.
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { listDrafts, createDraft } from "@/lib/collabApi";
import { CollabDraft, CollabDraftRequest, APIError } from "@/types/collab";
import CreateDraftModal from "@/components/CreateDraftModal";

export default function DraftsPage() {
  const router = useRouter();
  const [drafts, setDrafts] = useState<CollabDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    const loadDrafts = async () => {
      try {
        setLoading(true);
        const data = await listDrafts();
        setDrafts(data);
      } catch (err: any) {
        setError(err.message || "Failed to load drafts");
      } finally {
        setLoading(false);
      }
    };

    loadDrafts();
  }, []);

  const handleCreateDraft = async (request: CollabDraftRequest) => {
    try {
      setCreating(true);
      const draft = await createDraft(request);
      router.push(`/drafts/${draft.draft_id}`);
    } catch (err: any) {
      setError(err.message || "Failed to create draft");
    } finally {
      setCreating(false);
      setShowCreateModal(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-8">
        <div className="text-white">Loading drafts...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <h1 className="text-4xl font-bold text-white">Your Drafts</h1>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            + New Draft
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="mb-6 p-4 bg-red-500/20 border border-red-500 rounded-lg text-red-300">
            {error}
          </div>
        )}

        {/* Draft list */}
        {drafts.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-gray-400 text-lg">
              No drafts yet. Create one to get started!
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {drafts.map((draft) => (
              <DraftListItem key={draft.draft_id} draft={draft} />
            ))}
          </div>
        )}
      </div>

      {/* Create draft modal */}
      <CreateDraftModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        onSubmit={handleCreateDraft}
        isLoading={creating}
      />
    </div>
  );
}

/**
 * Individual draft list item.
 */
function DraftListItem({ draft }: { draft: CollabDraft }) {
  const isRingHolder = draft.ring_state.current_holder_id === localStorage.getItem("test_user_id");
  const platformColors: Record<string, string> = {
    x: "bg-blue-600",
    instagram: "bg-pink-600",
    tiktok: "bg-black",
    youtube: "bg-red-600",
  };

  return (
    <Link href={`/drafts/${draft.draft_id}`}>
      <div className="block p-4 bg-slate-800 rounded-lg border border-slate-700 hover:border-blue-500 transition cursor-pointer">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-white mb-2">
              {draft.title}
            </h3>
            <div className="flex items-center gap-2">
              <span
                className={`px-2 py-1 text-xs font-semibold text-white rounded ${
                  platformColors[draft.platform.toLowerCase()] || "bg-gray-600"
                }`}
              >
                {draft.platform}
              </span>
              <span className="text-sm text-gray-400">
                {draft.segments.length} segment{draft.segments.length !== 1 ? "s" : ""}
              </span>
              {isRingHolder && (
                <span className="text-lg">👑</span>
              )}
            </div>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500">
              {new Date(draft.updated_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>
    </Link>
  );
}
