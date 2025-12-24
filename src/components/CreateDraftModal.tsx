/**
 * Modal for creating a new draft.
 */

"use client";

import { useState } from "react";
import { CollabDraftRequest } from "@/types/collab";

interface CreateDraftModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (request: CollabDraftRequest) => Promise<void>;
  isLoading: boolean;
}

export default function CreateDraftModal({
  isOpen,
  onClose,
  onSubmit,
  isLoading,
}: CreateDraftModalProps) {
  const [title, setTitle] = useState("");
  const [platform, setPlatform] = useState("x");
  const [initialSegment, setInitialSegment] = useState("");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError("Title is required");
      return;
    }

    try {
      await onSubmit({
        title,
        platform,
        initial_segment: initialSegment || undefined,
      });
      // Reset form
      setTitle("");
      setPlatform("x");
      setInitialSegment("");
    } catch (err: any) {
      setError(err.message || "Failed to create draft");
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-800 rounded-lg border border-slate-700 max-w-md w-full p-6">
        <h2 className="text-2xl font-bold text-white mb-4">Create New Draft</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="My awesome draft..."
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
              disabled={isLoading}
            />
          </div>

          {/* Platform */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Platform
            </label>
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white focus:outline-none focus:border-blue-500 transition"
              disabled={isLoading}
            >
              <option value="x">X (Twitter)</option>
              <option value="instagram">Instagram</option>
              <option value="tiktok">TikTok</option>
              <option value="youtube">YouTube</option>
            </select>
          </div>

          {/* Initial segment */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Initial Segment (optional)
            </label>
            <textarea
              value={initialSegment}
              onChange={(e) => setInitialSegment(e.target.value)}
              placeholder="Start with some content..."
              maxLength={500}
              className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition resize-none h-24"
              disabled={isLoading}
            />
            <p className="text-xs text-gray-500 mt-1">
              {initialSegment.length}/500
            </p>
          </div>

          {/* Error */}
          {error && (
            <div className="p-3 bg-red-500/20 border border-red-500 rounded text-red-300 text-sm">
              {error}
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-600 transition disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50"
            >
              {isLoading ? "Creating..." : "Create Draft"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
