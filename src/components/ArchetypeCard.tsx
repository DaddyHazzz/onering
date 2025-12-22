/**
 * src/components/ArchetypeCard.tsx
 * Dashboard card showing user's creative archetype
 */

"use client";

import { useEffect, useState } from "react";

interface ArchetypeData {
  userId: string;
  primary: string;
  secondary: string | null;
  explanation: string[];
  updatedAt: string;
}

const ARCHETYPE_ICONS: Record<string, string> = {
  truth_teller: "🎯",
  builder: "🔨",
  philosopher: "💭",
  connector: "🤝",
  firestarter: "🔥",
  storyteller: "📖",
};

const ARCHETYPE_LABELS: Record<string, string> = {
  truth_teller: "Truth Teller",
  builder: "Builder",
  philosopher: "Philosopher",
  connector: "Connector",
  firestarter: "Firestarter",
  storyteller: "Storyteller",
};

export default function ArchetypeCard() {
  const [archetype, setArchetype] = useState<ArchetypeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchArchetype = async () => {
      try {
        const res = await fetch("/api/archetypes/me", { cache: "no-store" });
        const data = await res.json();

        if (res.ok && data.success) {
          setArchetype(data.data);
        } else {
          setError(data.error || "Failed to load archetype");
        }
      } catch (err) {
        console.error("[ArchetypeCard] fetch error:", err);
        setError("Network error");
      } finally {
        setLoading(false);
      }
    };

    fetchArchetype();
  }, []);

  if (loading) {
    return (
      <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-6 shadow-2xl">
        <div className="animate-pulse">
          <div className="h-6 bg-white/20 rounded w-1/3 mb-4"></div>
          <div className="h-4 bg-white/20 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error || !archetype) {
    return (
      <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-6 shadow-2xl">
        <p className="text-white/50 text-sm">
          {error || "No archetype data yet. Generate content to discover your style."}
        </p>
      </div>
    );
  }

  const primaryIcon = ARCHETYPE_ICONS[archetype.primary] || "✨";
  const primaryLabel = ARCHETYPE_LABELS[archetype.primary] || archetype.primary;
  const secondaryLabel = archetype.secondary
    ? ARCHETYPE_LABELS[archetype.secondary] || archetype.secondary
    : null;

  return (
    <div className="bg-gradient-to-br from-purple-600/30 to-blue-600/30 backdrop-blur-xl rounded-3xl p-6 shadow-2xl border border-white/10">
      <div className="flex items-center gap-3 mb-4">
        <span className="text-5xl">{primaryIcon}</span>
        <div>
          <h3 className="text-2xl font-bold text-white">
            {primaryLabel}
            {secondaryLabel && (
              <span className="text-lg font-normal text-white/70 ml-2">
                / {secondaryLabel}
              </span>
            )}
          </h3>
          <p className="text-sm text-white/50">Your Creative Archetype</p>
        </div>
      </div>

      <ul className="space-y-2 mb-4">
        {archetype.explanation.map((bullet, idx) => (
          <li key={idx} className="flex items-start gap-2 text-white/90 text-sm">
            <span className="text-purple-400 mt-0.5">•</span>
            <span>{bullet}</span>
          </li>
        ))}
      </ul>

      <p className="text-xs text-white/40 italic">
        Updates over time as you create and engage. Last updated:{" "}
        {new Date(archetype.updatedAt).toLocaleDateString()}
      </p>
    </div>
  );
}
