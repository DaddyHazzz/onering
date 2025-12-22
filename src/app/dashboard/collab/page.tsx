/**
 * src/app/dashboard/collab/page.tsx
 * Collaboration Threads with Invites: create, view, collaborate
 */

"use client";

import { useUser } from "@clerk/nextjs";
import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { v4 as uuidv4 } from "uuid";
import {
  shouldShowJoinedBanner,
  dismissJoinedBanner,
  getJoinedBannerMessage,
} from "@/features/collab/joinedBanner";
import { CollabShareCardModal } from "@/components/CollabShareCardModal";

interface DraftSegment {
  segment_id: string;
  content: string;
  user_id: string;
  created_at: string;
  segment_order: number;
  // Phase 3.3a: Attribution
  author_user_id?: string;
  author_display?: string;
  ring_holder_user_id_at_write?: string;
  ring_holder_display_at_write?: string;
}

interface RingState {
  current_holder_id: string;
  holders_history: string[];
  passed_at: string | null;
  last_passed_at?: string | null;  // Phase 3.3a: Track last pass time
}

interface DraftMetrics {
  contributorsCount: number;
  ringPassesLast24h: number;
  avgMinutesBetweenPasses: number | null;
  lastActivityAt: string;
}

interface CollabDraft {
  draft_id: string;
  creator_id: string;
  title: string;
  platform: "x" | "instagram" | "tiktok" | "youtube";
  status: "active" | "locked" | "completed";
  segments: DraftSegment[];
  ring_state: RingState;
  collaborators: string[];
  pending_invites: string[];
  created_at: string;
  updated_at: string;
  metrics?: DraftMetrics;  // Phase 3.3a: Ring velocity metrics
}

interface Invite {
  invite_id: string;
  draft_id: string;
  created_by_user_id: string;
  target_user_id: string;
  target_handle: string | null;
  status: "PENDING" | "ACCEPTED" | "REVOKED" | "EXPIRED";
  created_at: string;
  expires_at: string;
  accepted_at: string | null;
  token_hint: string;
}

export default function CollabPage() {
  const { user, isLoaded } = useUser();
  const searchParams = useSearchParams();
  const [drafts, setDrafts] = useState<CollabDraft[]>([]);
  const [selectedDraft, setSelectedDraft] = useState<CollabDraft | null>(null);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showJoinedBanner, setShowJoinedBanner] = useState(false);

  // Invite state
  const [inviteTarget, setInviteTarget] = useState("");
  const [inviteShareUrl, setInviteShareUrl] = useState<string | null>(null);
  const [inviteToken, setInviteToken] = useState<string | null>(null);

  // Form states
  const [createTitle, setCreateTitle] = useState("");
  const [createPlatform, setCreatePlatform] = useState<
    "x" | "instagram" | "tiktok" | "youtube"
  >("x");
  const [createInitial, setCreateInitial] = useState("");
  const [appendContent, setAppendContent] = useState("");
  const [passToUserId, setPassToUserId] = useState("");

  // Phase 3.3c: Share card modal
  const [showShareModal, setShowShareModal] = useState(false);

  if (!isLoaded) return <div>Loading...</div>;
  if (!user) return <div>Sign in required</div>;

  // Phase 3.3a: Helper to format relative time
  const formatRelativeTime = (isoTimestamp: string): string => {
    const now = new Date();
    const then = new Date(isoTimestamp);
    const diffMs = now.getTime() - then.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);
    
    if (diffMinutes < 1) return "just now";
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  // Fetch drafts
  const fetchDrafts = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("/api/collab/drafts");
      if (!res.ok) throw new Error("Failed to fetch drafts");
      const result = await res.json();
      setDrafts(result.data || []);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Fetch invites for a draft
  const fetchInvites = async (draftId: string) => {
    try {
      const res = await fetch(`/api/collab/drafts/${draftId}/invites`);
      if (!res.ok) {
        console.error("Failed to fetch invites");
        return;
      }
      const data = await res.json();
      setInvites(data.data || []);
    } catch (err: any) {
      console.error("Failed to fetch invites:", err);
    }
  };

  // Create draft
  const handleCreateDraft = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      setError(null);
      const res = await fetch("/api/collab/drafts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: createTitle,
          platform: createPlatform,
          initial_segment: createInitial,
        }),
      });
      if (!res.ok) throw new Error("Failed to create draft");
      const result = await res.json();
      setDrafts([...drafts, result.data]);
      setSelectedDraft(result.data);
      setCreateTitle("");
      setCreateInitial("");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Append segment
  const handleAppendSegment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDraft) return;

    // Check if current user is ring holder
    if (selectedDraft.ring_state.current_holder_id !== user.id) {
      setError("Only the ring holder can append segments");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await fetch(
        `/api/collab/drafts/${selectedDraft.draft_id}/segments`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            content: appendContent,
            idempotency_key: uuidv4(),
          }),
        }
      );
      if (!res.ok) throw new Error("Failed to append segment");
      const result = await res.json();
      setSelectedDraft(result.data);
      setDrafts(
        drafts.map((d) => (d.draft_id === selectedDraft.draft_id ? result.data : d))
      );
      setAppendContent("");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Pass ring
  const handlePassRing = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDraft) return;

    // Check if current user is ring holder
    if (selectedDraft.ring_state.current_holder_id !== user.id) {
      setError("Only the ring holder can pass the ring");
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const res = await fetch(
        `/api/collab/drafts/${selectedDraft.draft_id}/pass-ring`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            to_user_id: passToUserId,
            idempotency_key: uuidv4(),
          }),
        }
      );
      if (!res.ok) throw new Error("Failed to pass ring");
      const result = await res.json();
      setSelectedDraft(result.data);
      setDrafts(
        drafts.map((d) => (d.draft_id === selectedDraft.draft_id ? result.data : d))
      );
      setPassToUserId("");
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  // Invite collaborator
  const handleInviteCollaborator = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDraft) return;
    setLoading(true);
    setError(null);
    setInviteShareUrl(null);
    setInviteToken(null);
    try {
      const res = await fetch(
        `/api/collab/drafts/${selectedDraft.draft_id}/invites`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            target: inviteTarget,
          }),
        }
      );
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to create invite");
      }
      const data = await res.json();
      // Extract token from share_url if present
      const shareUrl = data.data.share_url;
      const tokenMatch = shareUrl?.match(/token=([^&]+)/);
      const token = tokenMatch ? tokenMatch[1] : null;
      setInviteShareUrl(shareUrl);
      setInviteToken(token);
      setInviteTarget("");
      fetchInvites(selectedDraft.draft_id);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Revoke invite
  const handleRevokeInvite = async (inviteId: string) => {
    if (!selectedDraft) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/collab/invites/${inviteId}/revoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          draftId: selectedDraft.draft_id,
        }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to revoke invite");
      }
      fetchInvites(selectedDraft.draft_id);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Copied!");
  };

  // Load drafts on mount
  useEffect(() => {
    if (user) fetchDrafts();
  }, [user]);

  // Auto-select draft from query params (Phase 3.3b)
  useEffect(() => {
    if (!user || drafts.length === 0) return;
    
    const draftIdParam = searchParams.get("draftId");
    const joinedParam = searchParams.get("joined");
    
    if (draftIdParam) {
      const matchingDraft = drafts.find((d) => d.draft_id === draftIdParam);
      if (matchingDraft) {
        setSelectedDraft(matchingDraft);
        // Check if banner should show
        if (typeof window !== "undefined") {
          const shouldShow = shouldShowJoinedBanner(
            window.localStorage,
            user.id,
            draftIdParam,
            joinedParam
          );
          setShowJoinedBanner(shouldShow);
        }
      }
    }
  }, [user, drafts, searchParams]);

  // Load invites when draft selected
  useEffect(() => {
    if (selectedDraft) {
      fetchInvites(selectedDraft.draft_id);
    }
  }, [selectedDraft]);

  const isRingHolder =
    selectedDraft &&
    selectedDraft.ring_state.current_holder_id === user.id;
  const isOwner = selectedDraft?.creator_id === user.id;
  const canInvite = isOwner || isRingHolder;

  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold">Collaboration Threads</h1>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded">
          <p className="text-red-900">{error}</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-8">
        {/* Left: Create & List */}
        <div className="space-y-6">
          {/* Create Draft Form */}
          <div className="p-6 bg-white border rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Create Draft</h2>
            <form onSubmit={handleCreateDraft} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Title</label>
                <input
                  type="text"
                  value={createTitle}
                  onChange={(e) => setCreateTitle(e.target.value)}
                  placeholder="Draft title (max 200 chars)"
                  maxLength={200}
                  required
                  className="w-full px-3 py-2 border rounded"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">Platform</label>
                <select
                  value={createPlatform}
                  onChange={(e) =>
                    setCreatePlatform(
                      e.target.value as "x" | "instagram" | "tiktok" | "youtube"
                    )
                  }
                  className="w-full px-3 py-2 border rounded"
                >
                  <option value="x">X (Twitter)</option>
                  <option value="instagram">Instagram</option>
                  <option value="tiktok">TikTok</option>
                  <option value="youtube">YouTube</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium mb-1">
                  Initial Segment (optional)
                </label>
                <textarea
                  value={createInitial}
                  onChange={(e) => setCreateInitial(e.target.value)}
                  placeholder="First segment (max 500 chars)"
                  maxLength={500}
                  rows={3}
                  className="w-full px-3 py-2 border rounded"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {loading ? "Creating..." : "Create Draft"}
              </button>
            </form>
          </div>

          {/* Drafts List */}
          <div className="p-6 bg-white border rounded-lg">
            <h2 className="text-xl font-semibold mb-4">Your Drafts</h2>
            {loading ? (
              <p>Loading...</p>
            ) : drafts.length === 0 ? (
              <p className="text-gray-600">No drafts yet</p>
            ) : (
              <div className="space-y-2">
                {drafts.map((draft) => (
                  <button
                    key={draft.draft_id}
                    onClick={() => setSelectedDraft(draft)}
                    className={`w-full p-3 rounded border text-left ${
                      selectedDraft?.draft_id === draft.draft_id
                        ? "bg-blue-50 border-blue-500"
                        : "hover:bg-gray-50"
                    }`}
                  >
                    <div className="font-medium">{draft.title}</div>
                    <div className="text-sm text-gray-600">
                      {draft.segments.length} segments · {draft.platform}
                    </div>
                    <div className="text-xs text-gray-500">
                      {draft.ring_state.current_holder_id === user.id
                        ? "🔴 You have the ring"
                        : `🔵 ${draft.ring_state.current_holder_id} has ring`}
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Draft Detail */}
        {selectedDraft ? (
          <div className="space-y-6">
            {/* Joined Banner - Phase 3.3b */}
            {showJoinedBanner && (
              <div className="p-4 bg-gradient-to-r from-green-50 to-blue-50 border border-green-300 rounded-lg">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-sm font-medium text-green-900">
                      {getJoinedBannerMessage({
                        userId: user.id,
                        draftId: selectedDraft.draft_id,
                        isRingHolder: selectedDraft.ring_state.current_holder_id === user.id,
                        ringHolderDisplay: selectedDraft.ring_state.current_holder_id,
                      })}
                    </p>
                  </div>
                  <div className="flex gap-2">
                    {selectedDraft.ring_state.current_holder_id === user.id && (
                      <button
                        onClick={() => {
                          // Scroll to pass ring section
                          document.getElementById("pass-ring-section")?.scrollIntoView({ behavior: "smooth" });
                        }}
                        className="px-3 py-1 text-xs bg-purple-600 text-white rounded hover:bg-purple-700"
                      >
                        Pass ring
                      </button>
                    )}
                    <button
                      onClick={() => {
                        if (typeof window !== "undefined") {
                          dismissJoinedBanner(window.localStorage, user.id, selectedDraft.draft_id);
                          setShowJoinedBanner(false);
                        }
                      }}
                      className="px-3 py-1 text-xs bg-white text-gray-700 border rounded hover:bg-gray-50"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Presence Card - Phase 3.3a */}
            <div className="p-4 bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium">
                    Ring is with{" "}
                    {selectedDraft.ring_state.current_holder_id === user.id
                      ? "you"
                      : selectedDraft.ring_state.current_holder_id}
                  </p>
                  {selectedDraft.ring_state.last_passed_at && (
                    <p className="text-xs text-gray-600 mt-1">
                      Last passed: {formatRelativeTime(selectedDraft.ring_state.last_passed_at)}
                    </p>
                  )}
                </div>
                {selectedDraft.ring_state.current_holder_id === user.id && (
                  <span className="px-3 py-1 bg-green-500 text-white text-sm font-medium rounded-full">
                    🔴 Your turn
                  </span>
                )}
              </div>
            </div>

            {/* Draft Info */}
            <div className="p-6 bg-white border rounded-lg">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold">{selectedDraft.title}</h2>
                <button
                  onClick={() => setShowShareModal(true)}
                  className="px-3 py-1 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700 transition"
                >
                  Share
                </button>
              </div>

              {/* Metrics Row - Phase 3.3a */}
              {selectedDraft.metrics && (
                <div className="flex gap-6 text-sm mb-4 pb-4 border-b">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-600">Contributors:</span>
                    <span className="font-semibold">{selectedDraft.metrics.contributorsCount}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-600">Passes (24h):</span>
                    <span className="font-semibold">{selectedDraft.metrics.ringPassesLast24h}</span>
                  </div>
                  {selectedDraft.metrics.avgMinutesBetweenPasses !== null && (
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-600">Avg:</span>
                      <span className="font-semibold">
                        {selectedDraft.metrics.avgMinutesBetweenPasses.toFixed(1)} min/pass
                      </span>
                    </div>
                  )}
                </div>
              )}

              <div className="space-y-2 text-sm mb-6">
                <div>
                  <span className="font-medium">Platform:</span>{" "}
                  <span className="capitalize">{selectedDraft.platform}</span>
                </div>
                <div>
                  <span className="font-medium">Status:</span>{" "}
                  <span className="capitalize">{selectedDraft.status}</span>
                </div>
                <div>
                  <span className="font-medium">Segments:</span>{" "}
                  <span>{selectedDraft.segments.length}</span>
                </div>
                <div>
                  <span className="font-medium">Ring Holder:</span>{" "}
                  <span>
                    {selectedDraft.ring_state.current_holder_id === user.id
                      ? "You 🔴"
                      : selectedDraft.ring_state.current_holder_id}
                  </span>
                </div>
                <div>
                  <span className="font-medium">History:</span>{" "}
                  <span>{selectedDraft.ring_state.holders_history.length} holders</span>
                </div>
              </div>

              {/* Segments */}
              <div className="border-t pt-4">
                <h3 className="font-semibold mb-3">Segments</h3>
                <div className="space-y-3 max-h-48 overflow-y-auto">
                  {selectedDraft.segments.map((seg) => {
                    const isRingHolder = seg.author_user_id === seg.ring_holder_user_id_at_write;
                    return (
                      <div
                        key={seg.segment_id}
                        className="p-3 bg-gray-50 rounded border-l-4 border-blue-500"
                      >
                        <div className="flex items-center gap-2 text-xs text-gray-600 mb-1">
                          <span>#{seg.segment_order + 1}</span>
                          <span>•</span>
                          <span>{seg.author_display || seg.user_id}</span>
                          {isRingHolder && (
                            <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs">
                              ring holder
                            </span>
                          )}
                        </div>
                        <div className="text-sm">{seg.content}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Collaborators */}
              {selectedDraft.collaborators && selectedDraft.collaborators.length > 0 && (
                <div className="border-t pt-4 mt-4">
                  <h3 className="font-semibold mb-2">Collaborators</h3>
                  <div className="space-y-1">
                    {selectedDraft.collaborators.map((collab) => (
                      <div key={collab} className="text-sm text-gray-700">
                        {collab} {collab === user.id && "(You)"}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Invite Collaborator */}
            {canInvite && (
              <div className="p-6 bg-purple-50 border border-purple-200 rounded-lg">
                <h3 className="font-semibold mb-4">Invite Collaborator</h3>
                <form onSubmit={handleInviteCollaborator} className="space-y-3">
                  <input
                    type="text"
                    value={inviteTarget}
                    onChange={(e) => setInviteTarget(e.target.value)}
                    placeholder="@handle or user_id"
                    required
                    className="w-full px-3 py-2 border rounded"
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
                  >
                    {loading ? "Inviting..." : "Send Invite"}
                  </button>
                </form>

                {inviteShareUrl && (
                  <div className="mt-4 p-3 bg-white border border-purple-300 rounded">
                    <p className="text-sm font-medium mb-2">
                      ✅ Invite created! Share this link:
                    </p>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        value={inviteShareUrl}
                        readOnly
                        className="flex-1 px-2 py-1 text-sm bg-gray-50 border rounded"
                      />
                      <button
                        onClick={() => copyToClipboard(inviteShareUrl)}
                        className="px-3 py-1 text-sm bg-purple-600 text-white rounded hover:bg-purple-700"
                      >
                        Copy
                      </button>
                    </div>
                    {inviteToken && (
                      <p className="text-xs text-gray-600 mt-2">
                        Token hint: ...{inviteToken.slice(-6)}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* Pending Invites */}
            {invites.length > 0 && (
              <div className="p-6 bg-white border rounded-lg">
                <h3 className="font-semibold mb-4">Invites</h3>
                <div className="space-y-2">
                  {invites.map((invite) => (
                    <div
                      key={invite.invite_id}
                      className="flex justify-between items-center p-3 bg-gray-50 rounded border"
                    >
                      <div>
                        <p className="text-sm font-medium">
                          {invite.target_handle || invite.target_user_id}
                        </p>
                        <p className="text-xs text-gray-600">
                          {invite.status === "PENDING" && "⏳ Pending"}
                          {invite.status === "ACCEPTED" && "✅ Accepted"}
                          {invite.status === "REVOKED" && "🚫 Revoked"}
                          {invite.status === "EXPIRED" && "⌛ Expired"}
                          {" • Token: ..."}
                          {invite.token_hint}
                        </p>
                      </div>
                      {invite.status === "PENDING" && canInvite && (
                        <button
                          onClick={() => handleRevokeInvite(invite.invite_id)}
                          disabled={loading}
                          className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
                        >
                          Revoke
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Append Segment */}
            {isRingHolder && (
              <div className="p-6 bg-blue-50 border border-blue-200 rounded-lg">
                <h3 className="font-semibold mb-4">Add Your Segment</h3>
                <form onSubmit={handleAppendSegment} className="space-y-3">
                  <textarea
                    value={appendContent}
                    onChange={(e) => setAppendContent(e.target.value)}
                    placeholder="Your segment (max 500 chars)"
                    maxLength={500}
                    rows={4}
                    required
                    className="w-full px-3 py-2 border rounded"
                  />
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? "Adding..." : "Add Segment"}
                  </button>
                </form>
              </div>
            )}

            {/* Pass Ring */}
            {isRingHolder && (
              <div id="pass-ring-section" className="p-6 bg-green-50 border border-green-200 rounded-lg">
                <h3 className="font-semibold mb-4">Pass the Ring</h3>
                <form onSubmit={handlePassRing} className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      To User ID
                    </label>
                    <input
                      type="text"
                      value={passToUserId}
                      onChange={(e) => setPassToUserId(e.target.value)}
                      placeholder="Collaborator's user ID"
                      required
                      className="w-full px-3 py-2 border rounded"
                    />
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                  >
                    {loading ? "Passing..." : "Pass Ring"}
                  </button>
                </form>
              </div>
            )}

            {!isRingHolder && (
              <div className="p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  💡 You're not the current ring holder. Wait for the ring to be
                  passed to you to add segments.
                </p>
              </div>
            )}
          </div>
        ) : (
          <div className="p-6 bg-gray-50 border rounded-lg text-center">
            <p className="text-gray-600">
              Select a draft to view details and collaborate
            </p>
          </div>
        )}
      </div>

      {/* Share Card Modal - Phase 3.3c */}
      {selectedDraft && (
        <CollabShareCardModal
          draftId={selectedDraft.draft_id}
          isOpen={showShareModal}
          onClose={() => setShowShareModal(false)}
        />
      )}
    </div>
  );
}
