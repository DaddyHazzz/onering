"use client";

import { useUser } from "@clerk/nextjs";
import { useState, useEffect } from "react";
import { Leaderboard } from "@/app/api/analytics/leaderboard/route";

interface ActivityCard {
  label: string;
  value: number | string;
  unit: string;
  insight: string;
}

export default function InsightsPage() {
  const { user, isLoaded } = useUser();
  const [leaderboard, setLeaderboard] = useState<Leaderboard | null>(null);
  const [metric, setMetric] = useState<"collaboration" | "momentum" | "consistency">("collaboration");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded || !user) return;

    const fetchLeaderboard = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/analytics/leaderboard?metric=${metric}`);
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.error || "Failed to fetch leaderboard");
        }
        const data = await res.json();
        setLeaderboard(data);
      } catch (e: any) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };

    fetchLeaderboard();
  }, [isLoaded, user, metric]);

  if (!isLoaded) return <div className="p-6">Loading...</div>;
  if (!user) return <div className="p-6">Sign in required</div>;

  const activityCards: ActivityCard[] = [
    {
      label: "Drafts Contributed",
      value: "3",
      unit: "collaborations",
      insight: "Growing your collaboration skills",
    },
    {
      label: "Segments Written",
      value: "12",
      unit: "segments",
      insight: "Building momentum through consistent contribution",
    },
    {
      label: "RING Held",
      value: "2",
      unit: "times",
      insight: "Trusted by collaborators",
    },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Your Insights</h1>
          <p className="text-lg text-slate-600">Reflect on your progress, celebrate growth</p>
        </div>

        {/* Your Activity Section */}
        <section className="mb-12">
          <h2 className="text-2xl font-bold text-slate-800 mb-4">Your Activity</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {activityCards.map((card, i) => (
              <div
                key={i}
                className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm hover:shadow-md transition-shadow"
              >
                <p className="text-sm text-slate-500 font-medium mb-2">{card.label}</p>
                <p className="text-3xl font-bold text-slate-900 mb-1">{card.value}</p>
                <p className="text-xs text-slate-400 mb-3">{card.unit}</p>
                <p className="text-sm text-slate-600 italic">{card.insight}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Community Momentum Section */}
        <section>
          <h2 className="text-2xl font-bold text-slate-800 mb-4">Community Momentum</h2>

          {/* Metric Selector */}
          <div className="flex gap-2 mb-6">
            {(["collaboration", "momentum", "consistency"] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMetric(m)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  metric === m
                    ? "bg-blue-600 text-white"
                    : "bg-white text-slate-700 border border-slate-300 hover:bg-slate-50"
                }`}
              >
                {m.charAt(0).toUpperCase() + m.slice(1)}
              </button>
            ))}
          </div>

          {/* Leaderboard */}
          {loading && <div className="text-center py-8 text-slate-500">Loading leaderboard...</div>}
          {error && <div className="text-center py-8 text-red-600">Error: {error}</div>}

          {leaderboard && (
            <div className="bg-white rounded-lg border border-slate-200 p-6 shadow-sm">
              <p className="text-sm text-slate-600 mb-4 italic">{leaderboard.data.message}</p>

              {leaderboard.data.entries.length === 0 ? (
                <p className="text-center text-slate-500 py-8">No entries yet</p>
              ) : (
                <div className="space-y-3">
                  {leaderboard.data.entries.slice(0, 3).map((entry) => (
                    <div key={entry.position} className="flex items-center gap-4 pb-3 border-b border-slate-100 last:border-0">
                      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white font-bold">
                        {entry.position}
                      </div>
                      <div className="flex-1">
                        <p className="font-medium text-slate-900">{entry.display_name}</p>
                        <p className="text-sm text-slate-500">{entry.metric_label}</p>
                      </div>
                      <p className="text-sm text-slate-600 italic">{entry.insight}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>

        {/* Supportive Message */}
        <div className="mt-12 p-6 bg-blue-50 border border-blue-200 rounded-lg">
          <p className="text-blue-900">
            <strong>💡 Tip:</strong> Insights are here to support your growth, not to measure yourself against others. Focus on consistency and collaboration—everything else follows.
          </p>
        </div>
      </div>
    </div>
  );
}
