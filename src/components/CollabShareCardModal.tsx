"use client";

import { useState } from "react";
import { ShareCard } from "@/app/api/collab/drafts/[draftId]/share-card/route";

interface CollabShareCardModalProps {
  draftId: string;
  isOpen: boolean;
  onClose: () => void;
}

export function CollabShareCardModal({
  draftId,
  isOpen,
  onClose,
}: CollabShareCardModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shareCard, setShareCard] = useState<ShareCard | null>(null);
  const [copied, setCopied] = useState(false);

  const fetchShareCard = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/collab/drafts/${draftId}/share-card`);
      if (!response.ok) throw new Error("Failed to fetch share card");

      const data = await response.json();
      if (!data.data) throw new Error("Invalid share card response");

      setShareCard(data.data);
    } catch (err: any) {
      setError(err.message || "Failed to load share card");
    } finally {
      setLoading(false);
    }
  };

  const copyShareLink = () => {
    if (!shareCard?.cta.url) return;

    const fullUrl = `${window.location.origin}${shareCard.cta.url}`;
    navigator.clipboard.writeText(fullUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyCardJSON = () => {
    if (!shareCard) return;

    navigator.clipboard.writeText(JSON.stringify(shareCard, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-lg max-w-md w-full mx-4 max-h-96 overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-lg font-semibold">Share Card</h2>
          <button
            onClick={onClose}
            className="text-gray-500 hover:text-gray-700 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {error && (
            <div className="bg-red-50 border border-red-200 rounded p-3 text-red-700 text-sm mb-4">
              {error}
            </div>
          )}

          {loading && !shareCard && (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
              <p className="text-gray-600 mt-2">Loading share card...</p>
            </div>
          )}

          {shareCard && (
            <div className="space-y-4">
              {/* Preview */}
              <div className={`rounded-lg p-4 bg-gradient-to-br ${shareCard.theme.bg} text-white`}>
                <h3 className="font-bold text-lg mb-2">{shareCard.title}</h3>
                <p className="text-sm opacity-90 mb-3">{shareCard.subtitle}</p>

                {/* Contributors chips */}
                <div className="flex flex-wrap gap-2 mb-3">
                  {shareCard.contributors.map((contributor) => (
                    <span
                      key={contributor}
                      className="bg-white bg-opacity-20 rounded-full px-3 py-1 text-xs font-medium"
                    >
                      {contributor}
                    </span>
                  ))}
                </div>

                {/* Metrics row */}
                <div className="text-xs opacity-75 space-y-1">
                  <div>
                    <strong>{shareCard.metrics.contributors_count}</strong>{" "}
                    contributors
                  </div>
                  <div>
                    <strong>{shareCard.metrics.ring_passes_last_24h}</strong> passes
                    in 24h
                  </div>
                  {shareCard.metrics.avg_minutes_between_passes !== null && (
                    <div>
                      Avg{" "}
                      <strong>
                        {shareCard.metrics.avg_minutes_between_passes}
                      </strong>{" "}
                      min between passes
                    </div>
                  )}
                </div>

                {/* CTA Preview */}
                <button className="mt-4 w-full bg-white text-indigo-700 font-semibold py-2 rounded hover:bg-opacity-90 transition disabled">
                  {shareCard.cta.label}
                </button>
              </div>

              {/* Description */}
              <p className="text-sm text-gray-700">{shareCard.top_line}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-2 p-6 border-t bg-gray-50">
          <button
            onClick={fetchShareCard}
            disabled={loading}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 transition disabled:opacity-50"
          >
            {loading ? "Loading..." : "Refresh"}
          </button>
          <button
            onClick={copyShareLink}
            className="flex-1 px-4 py-2 border border-indigo-600 text-indigo-600 rounded hover:bg-indigo-50 transition"
          >
            {copied ? "Copied!" : "Copy Link"}
          </button>
          <button
            onClick={copyCardJSON}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded hover:bg-gray-100 transition"
          >
            Copy JSON
          </button>
        </div>
      </div>
    </div>
  );
}
