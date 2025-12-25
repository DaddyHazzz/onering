/**
 * WaitForRingPanel - Phase 8.4 "Waiting for the Ring" mode
 * 
 * When you don't hold the ring, you can still be productive:
 * - Private Notes: Scratch pad for your ideas
 * - Queued Suggestions: Queue ideas for the ring holder
 * - Votes: Upvote/downvote segments
 * 
 * Ring holder sees queued suggestions with "consume" action.
 */

"use client";

import React, { useState, useEffect } from "react";
import {
  ScratchNote,
  QueuedSuggestion,
  VoteSummary,
  SuggestionKind,
  SuggestionStatus,
} from "@/types/collab";
import {
  createNote,
  listNotes,
  updateNote,
  deleteNote,
  createSuggestion,
  listSuggestions,
  dismissSuggestion,
  consumeSuggestion,
  voteSegment,
  listVotes,
} from "@/lib/collabApi";

interface WaitForRingPanelProps {
  draftId: string;
  isRingHolder: boolean;
  userId: string;
  segments: Array<{ segment_id: string; content: string }>;
  onConsumeSuggestion?: (content: string) => void;
}

type Tab = "notes" | "suggestions" | "votes";

export default function WaitForRingPanel({
  draftId,
  isRingHolder,
  userId,
  segments,
  onConsumeSuggestion,
}: WaitForRingPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("notes");
  const [notes, setNotes] = useState<ScratchNote[]>([]);
  const [suggestions, setSuggestions] = useState<QueuedSuggestion[]>([]);
  const [votes, setVotes] = useState<VoteSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Notes state
  const [newNoteContent, setNewNoteContent] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");

  // Suggestions state
  const [newSuggestionContent, setNewSuggestionContent] = useState("");
  const [selectedKind, setSelectedKind] = useState<SuggestionKind>("idea");
  const [suggestionFilter, setSuggestionFilter] = useState<SuggestionStatus | undefined>(undefined);

  useEffect(() => {
    loadData();
  }, [draftId, activeTab, suggestionFilter]);

  async function loadData() {
    setLoading(true);
    setError(null);
    try {
      if (activeTab === "notes") {
        const data = await listNotes(draftId);
        setNotes(data);
      } else if (activeTab === "suggestions") {
        const data = await listSuggestions(draftId, suggestionFilter);
        setSuggestions(data);
      } else if (activeTab === "votes") {
        const data = await listVotes(draftId);
        setVotes(data.segments);
      }
    } catch (err: any) {
      setError(err.message || "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  // ===== NOTES ACTIONS =====

  async function handleCreateNote() {
    if (!newNoteContent.trim()) return;
    try {
      await createNote(draftId, { content: newNoteContent });
      setNewNoteContent("");
      loadData();
    } catch (err: any) {
      setError(err.message || "Failed to create note");
    }
  }

  async function handleUpdateNote(noteId: string) {
    if (!editContent.trim()) return;
    try {
      await updateNote(noteId, { content: editContent });
      setEditingNoteId(null);
      setEditContent("");
      loadData();
    } catch (err: any) {
      setError(err.message || "Failed to update note");
    }
  }

  async function handleDeleteNote(noteId: string) {
    if (!confirm("Delete this note?")) return;
    try {
      await deleteNote(noteId);
      loadData();
    } catch (err: any) {
      setError(err.message || "Failed to delete note");
    }
  }

  // ===== SUGGESTIONS ACTIONS =====

  async function handleCreateSuggestion() {
    if (!newSuggestionContent.trim()) return;
    try {
      await createSuggestion(draftId, { kind: selectedKind, content: newSuggestionContent });
      setNewSuggestionContent("");
      loadData();
    } catch (err: any) {
      setError(err.message || "Failed to create suggestion");
    }
  }

  async function handleDismissSuggestion(suggestionId: string) {
    try {
      await dismissSuggestion(suggestionId);
      loadData();
    } catch (err: any) {
      setError(err.message || "Failed to dismiss suggestion");
    }
  }

  async function handleConsumeSuggestion(suggestion: QueuedSuggestion) {
    if (!isRingHolder) return;
    try {
      const lastSegmentId = segments[segments.length - 1]?.segment_id || "";
      await consumeSuggestion(suggestion.suggestion_id, lastSegmentId);
      if (onConsumeSuggestion) {
        onConsumeSuggestion(suggestion.content);
      }
      loadData();
    } catch (err: any) {
      setError(err.message || "Failed to consume suggestion");
    }
  }

  // ===== VOTES ACTIONS =====

  async function handleVote(segmentId: string, value: 1 | -1) {
    try {
      await voteSegment(draftId, segmentId, { value });
      loadData();
    } catch (err: any) {
      setError(err.message || "Failed to vote");
    }
  }

  // ===== RENDER =====

  const tabs: { id: Tab; label: string }[] = [
    { id: "notes", label: "📝 Notes" },
    { id: "suggestions", label: "💡 Suggestions" },
    { id: "votes", label: "👍 Votes" },
  ];

  return (
    <div className="border border-gray-300 rounded-lg p-4 bg-white shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          {isRingHolder ? "🔔 Queued Suggestions & Activity" : "⏳ Waiting for the Ring"}
        </h3>
        <span className="text-xs text-gray-500">
          {isRingHolder ? "You hold the ring" : "Contribute while you wait"}
        </span>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 mb-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 font-medium text-sm transition-colors ${
              activeTab === tab.id
                ? "border-b-2 border-blue-600 text-blue-600"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Loading spinner */}
      {loading && (
        <div className="flex justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        </div>
      )}

      {/* Tab content */}
      {!loading && (
        <>
          {activeTab === "notes" && (
            <div className="space-y-4">
              {/* Create note */}
              <div className="border border-gray-200 rounded p-3 bg-gray-50">
                <textarea
                  value={newNoteContent}
                  onChange={(e) => setNewNoteContent(e.target.value)}
                  placeholder="Quick note for yourself..."
                  className="w-full p-2 border border-gray-300 rounded resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={3}
                  maxLength={2000}
                />
                <div className="flex justify-between items-center mt-2">
                  <span className="text-xs text-gray-500">{newNoteContent.length}/2000</span>
                  <button
                    onClick={handleCreateNote}
                    disabled={!newNoteContent.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                  >
                    Save Note
                  </button>
                </div>
              </div>

              {/* List notes */}
              {notes.length === 0 && (
                <p className="text-center text-gray-500 text-sm py-4">No notes yet. Start jotting down ideas!</p>
              )}
              {notes.map((note) => (
                <div key={note.note_id} className="border border-gray-200 rounded p-3 bg-white">
                  {editingNoteId === note.note_id ? (
                    <>
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="w-full p-2 border border-gray-300 rounded resize-none"
                        rows={3}
                        maxLength={2000}
                      />
                      <div className="flex gap-2 mt-2">
                        <button
                          onClick={() => handleUpdateNote(note.note_id)}
                          className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => {
                            setEditingNoteId(null);
                            setEditContent("");
                          }}
                          className="px-3 py-1 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 text-sm"
                        >
                          Cancel
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <p className="text-gray-900 whitespace-pre-wrap">{note.content}</p>
                      <div className="flex justify-between items-center mt-2">
                        <span className="text-xs text-gray-500">
                          {new Date(note.updated_at).toLocaleString()}
                        </span>
                        <div className="flex gap-2">
                          <button
                            onClick={() => {
                              setEditingNoteId(note.note_id);
                              setEditContent(note.content);
                            }}
                            className="text-blue-600 hover:underline text-sm"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleDeleteNote(note.note_id)}
                            className="text-red-600 hover:underline text-sm"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          )}

          {activeTab === "suggestions" && (
            <div className="space-y-4">
              {/* Create suggestion */}
              <div className="border border-gray-200 rounded p-3 bg-gray-50">
                <div className="flex gap-2 mb-2">
                  {(["idea", "rewrite", "next_segment", "title", "cta"] as SuggestionKind[]).map((kind) => (
                    <button
                      key={kind}
                      onClick={() => setSelectedKind(kind)}
                      className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                        selectedKind === kind
                          ? "bg-blue-600 text-white"
                          : "bg-white text-gray-700 border border-gray-300 hover:bg-gray-100"
                      }`}
                    >
                      {kind}
                    </button>
                  ))}
                </div>
                <textarea
                  value={newSuggestionContent}
                  onChange={(e) => setNewSuggestionContent(e.target.value)}
                  placeholder={`Queue a ${selectedKind} for the ring holder...`}
                  className="w-full p-2 border border-gray-300 rounded resize-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  rows={3}
                  maxLength={1000}
                />
                <div className="flex justify-between items-center mt-2">
                  <span className="text-xs text-gray-500">{newSuggestionContent.length}/1000</span>
                  <button
                    onClick={handleCreateSuggestion}
                    disabled={!newSuggestionContent.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
                  >
                    Queue Suggestion
                  </button>
                </div>
              </div>

              {/* Filter suggestions */}
              <div className="flex gap-2">
                <button
                  onClick={() => setSuggestionFilter(undefined)}
                  className={`px-3 py-1 rounded text-sm ${
                    suggestionFilter === undefined ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-700"
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setSuggestionFilter("queued")}
                  className={`px-3 py-1 rounded text-sm ${
                    suggestionFilter === "queued" ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-700"
                  }`}
                >
                  Queued
                </button>
                <button
                  onClick={() => setSuggestionFilter("consumed")}
                  className={`px-3 py-1 rounded text-sm ${
                    suggestionFilter === "consumed" ? "bg-green-600 text-white" : "bg-gray-200 text-gray-700"
                  }`}
                >
                  Consumed
                </button>
                <button
                  onClick={() => setSuggestionFilter("dismissed")}
                  className={`px-3 py-1 rounded text-sm ${
                    suggestionFilter === "dismissed" ? "bg-gray-600 text-white" : "bg-gray-200 text-gray-700"
                  }`}
                >
                  Dismissed
                </button>
              </div>

              {/* List suggestions */}
              {suggestions.length === 0 && (
                <p className="text-center text-gray-500 text-sm py-4">No suggestions yet. Queue an idea!</p>
              )}
              {suggestions.map((sug) => (
                <div key={sug.suggestion_id} className="border border-gray-200 rounded p-3 bg-white">
                  <div className="flex justify-between items-start mb-2">
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs font-medium">
                      {sug.kind}
                    </span>
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        sug.status === "queued"
                          ? "bg-yellow-100 text-yellow-800"
                          : sug.status === "consumed"
                          ? "bg-green-100 text-green-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {sug.status}
                    </span>
                  </div>
                  <p className="text-gray-900 whitespace-pre-wrap mb-2">{sug.content}</p>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-500">{new Date(sug.created_at).toLocaleString()}</span>
                    <div className="flex gap-2">
                      {isRingHolder && sug.status === "queued" && (
                        <button
                          onClick={() => handleConsumeSuggestion(sug)}
                          className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 text-sm font-medium"
                        >
                          ✅ Insert as Next
                        </button>
                      )}
                      {sug.author_user_id === userId && sug.status === "queued" && (
                        <button
                          onClick={() => handleDismissSuggestion(sug.suggestion_id)}
                          className="px-3 py-1 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 text-sm"
                        >
                          Dismiss
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {activeTab === "votes" && (
            <div className="space-y-4">
              {segments.length === 0 && (
                <p className="text-center text-gray-500 text-sm py-4">No segments yet.</p>
              )}
              {segments.map((seg) => {
                const voteSummary = votes.find((v) => v.segment_id === seg.segment_id);
                const userVote = voteSummary?.user_vote;
                return (
                  <div key={seg.segment_id} className="border border-gray-200 rounded p-3 bg-white">
                    <p className="text-gray-900 mb-3 whitespace-pre-wrap">{seg.content}</p>
                    <div className="flex items-center gap-4">
                      <button
                        onClick={() => handleVote(seg.segment_id, 1)}
                        className={`flex items-center gap-1 px-3 py-1 rounded transition-colors ${
                          userVote === 1
                            ? "bg-green-600 text-white"
                            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                        }`}
                      >
                        👍 {voteSummary?.upvotes || 0}
                      </button>
                      <button
                        onClick={() => handleVote(seg.segment_id, -1)}
                        className={`flex items-center gap-1 px-3 py-1 rounded transition-colors ${
                          userVote === -1
                            ? "bg-red-600 text-white"
                            : "bg-gray-100 text-gray-700 hover:bg-gray-200"
                        }`}
                      >
                        👎 {voteSummary?.downvotes || 0}
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}
