/**
 * src/components/ShareCardModal.tsx
 * Modal preview of share card + copy button.
 */

"use client";

import { useState } from "react";

interface ShareCardData {
  title: string;
  subtitle: string;
  metrics: {
    streak: number;
    momentum_score: number;
    weekly_delta: number;
    top_platform: string;
  };
  tagline: string;
  theme: {
    bg: string;
    accent: string;
  };
}

interface ShareCardModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: ShareCardData | null;
  handle: string;
  loading: boolean;
}

export function ShareCardModal({
  isOpen,
  onClose,
  data,
  handle,
  loading,
}: ShareCardModalProps) {
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleCopyLink = () => {
    const url = `${window.location.origin}/u/${handle}`;
    navigator.clipboard.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyJSON = () => {
    if (data) {
      navigator.clipboard.writeText(JSON.stringify(data, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-slate-900 rounded-2xl max-w-2xl w-full max-h-[80vh] overflow-y-auto border border-purple-500/30">
        {/* Header */}
        <div className="sticky top-0 border-b border-purple-500/30 bg-slate-900 p-6 flex justify-between items-center">
          <h2 className="text-2xl font-bold text-white">Share Card Preview</h2>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white text-2xl"
          >
            ×
          </button>
        </div>

        {/* Content */}
        <div className="p-6 space-y-6">
          {loading ? (
            <div className="text-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400 mx-auto mb-2" />
              <p className="text-white/60">Generating...</p>
            </div>
          ) : data ? (
            <>
              {/* Card Preview */}
              <div
                className={`bg-gradient-to-r ${data.theme.bg} rounded-xl p-8 text-white`}
              >
                <h3 className="text-4xl font-black mb-2">{data.title}</h3>
                <p className="text-lg mb-6 opacity-90">{data.subtitle}</p>

                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div className="bg-white/10 rounded-lg p-4">
                    <p className="text-sm opacity-75">Streak</p>
                    <p className="text-3xl font-bold">{data.metrics.streak}</p>
                  </div>
                  <div className="bg-white/10 rounded-lg p-4">
                    <p className="text-sm opacity-75">Momentum</p>
                    <p className="text-3xl font-bold">{data.metrics.momentum_score}</p>
                  </div>
                  <div className="bg-white/10 rounded-lg p-4">
                    <p className="text-sm opacity-75">Weekly</p>
                    <p className="text-3xl font-bold">
                      {data.metrics.weekly_delta > 0 ? '+' : ''}{data.metrics.weekly_delta}
                    </p>
                  </div>
                  <div className="bg-white/10 rounded-lg p-4">
                    <p className="text-sm opacity-75">Platform</p>
                    <p className="text-2xl font-bold">{data.metrics.top_platform}</p>
                  </div>
                </div>

                <p className="italic text-lg opacity-90 border-t border-white/20 pt-4">
                  "{data.tagline}"
                </p>
              </div>

              {/* Raw JSON */}
              <div className="bg-white/5 rounded-lg p-4 border border-white/10">
                <p className="text-sm text-white/60 mb-2">Raw JSON:</p>
                <pre className="text-xs text-white/70 overflow-x-auto bg-black/30 p-3 rounded">
                  {JSON.stringify(data, null, 2)}
                </pre>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={handleCopyLink}
                  className="flex-1 px-4 py-2 bg-purple-500 hover:bg-purple-600 rounded-lg font-medium text-white"
                >
                  {copied ? "✓ Copied Profile Link" : "Copy Profile Link"}
                </button>
                <button
                  onClick={handleCopyJSON}
                  className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg font-medium text-white text-sm"
                >
                  {copied ? "✓ Copied JSON" : "Copy JSON"}
                </button>
              </div>
            </>
          ) : (
            <p className="text-white/60 text-center py-8">No data available</p>
          )}
        </div>
      </div>
    </div>
  );
}
