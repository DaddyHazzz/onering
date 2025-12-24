/**
 * Draft detail page: /drafts/[id]
 * Shows draft editor with ring-based edit locking.
 */

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getDraft, appendSegment, passRing, isRingRequiredError, addCollaborator } from "@/lib/collabApi";
import { CollabDraft, APIError } from "@/types/collab";
import DraftEditor from "@/components/DraftEditor";
import SegmentTimeline from "@/components/SegmentTimeline";
import RingControls from "@/components/RingControls";
import CollaboratorPanel from "@/components/CollaboratorPanel";
import { v4 as uuidv4 } from "uuid";

export default function DraftDetailPage() {
  const params = useParams();
  const draftId = params.id as string;
  const currentUserId = typeof window !== "undefined" ? localStorage.getItem("test_user_id") || "" : "";

  const [draft, setDraft] = useState<CollabDraft | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ringRequiredError, setRingRequiredError] = useState(false);
  const [appending, setAppending] = useState(false);
  const [passingRing, setPassingRing] = useState(false);
  const [addingCollaborator, setAddingCollaborator] = useState(false);

  const isRingHolder = draft?.ring_state.current_holder_id === currentUserId;
  const isCreator = draft?.creator_id === currentUserId;

  useEffect(() => {
    const loadDraft = async () => {
      try {
        setLoading(true);
        const data = await getDraft(draftId);
        setDraft(data);
        setError(null);
        setRingRequiredError(false);
      } catch (err: any) {
        setError(err.message || "Failed to load draft");
      } finally {
        setLoading(false);
      }
    };

    loadDraft();
  }, [draftId]);

  const handleAppendSegment = async (content: string) => {
    if (!draft) return;

    try {
      setAppending(true);
      setRingRequiredError(false);
      const request = {
        content,
        idempotency_key: uuidv4(),
      };

      const updated = await appendSegment(draftId, request);
      setDraft(updated);
    } catch (err: any) {
      if (isRingRequiredError(err)) {
        setRingRequiredError(true);
        // Refresh draft to get latest state
        try {
          const updated = await getDraft(draftId);
          setDraft(updated);
        } catch {}
      } else {
        setError(err.message || "Failed to append segment");
      }
    } finally {
      setAppending(false);
    }
  };

  const handlePassRing = async (toUserId: string) => {
    if (!draft) return;

    try {
      setPassingRing(true);
      const request = {
        to_user_id: toUserId,
        idempotency_key: uuidv4(),
      };

      const updated = await passRing(draftId, request);
      setDraft(updated);
    } catch (err: any) {
      setError(err.message || "Failed to pass ring");
    } finally {
      setPassingRing(false);
    }
  };

  const handleAddCollaborator = async (collaboratorId: string) => {
    if (!draft) return;

    try {
      setAddingCollaborator(true);
      const updated = await addCollaborator(draftId, collaboratorId);
      setDraft(updated);
    } catch (err: any) {
      setError(err.message || "Failed to add collaborator");
    } finally {
      setAddingCollaborator(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-8">
        <div className="text-white">Loading draft...</div>
      </div>
    );
  }

  if (!draft) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-8">
        <div className="max-w-4xl mx-auto">
          <div className="p-4 bg-red-500/20 border border-red-500 rounded-lg text-red-300">
            Draft not found
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 to-slate-800 p-8">
      <div className="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main editor area */}
        <div className="lg:col-span-2 space-y-6">
          {/* Header */}
          <div className="bg-slate-800 rounded-lg border border-slate-700 p-6">
            <h1 className="text-3xl font-bold text-white mb-2">{draft.title}</h1>
            <div className="flex items-center gap-3 flex-wrap">
              <span className="text-sm text-gray-400">
                Platform: <span className="text-white font-semibold">{draft.platform.toUpperCase()}</span>
              </span>
              {isRingHolder ? (
                <span className="text-sm text-yellow-400">👑 You hold the ring</span>
              ) : (
                <span className="text-sm text-gray-400">
                  Waiting for <span className="text-white font-semibold">@{draft.ring_state.current_holder_id}</span>
                </span>
              )}
            </div>
          </div>

          {/* Error messages */}
          {error && (
            <div className="p-4 bg-red-500/20 border border-red-500 rounded-lg text-red-300">
              {error}
            </div>
          )}

          {ringRequiredError && (
            <div className="p-4 bg-yellow-500/20 border border-yellow-500 rounded-lg text-yellow-300">
              You don't hold the ring. Only the ring holder can append segments.
            </div>
          )}

          {/* Editor */}
          <DraftEditor
            draft={draft}
            isRingHolder={isRingHolder}
            onAppendSegment={handleAppendSegment}
            isAppending={appending}
          />

          {/* Segments timeline */}
          <SegmentTimeline segments={draft.segments} />
        </div>

        {/* Sidebar: Ring controls + collaborators */}
        <div className="space-y-6">
          {/* Ring controls */}
          <RingControls
            draft={draft}
            isRingHolder={isRingHolder}
            onPassRing={handlePassRing}
            isLoading={passingRing}
          />

          {/* Collaborator panel */}
          <CollaboratorPanel
            draft={draft}
            isCreator={isCreator}
            onAddCollaborator={handleAddCollaborator}
            isLoading={addingCollaborator}
          />
        </div>
      </div>
    </div>
  );
}
