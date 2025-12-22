"use client";

/**
 * src/app/today/page.tsx
 * Daily ritual homepage: Streak + Challenge + Coach + Momentum + Archetype
 * Answers "What matters right now?" in one glance.
 */

import { useUser } from "@clerk/nextjs";
import { useState, useEffect } from "react";
import Link from "next/link";

interface StreakData {
  current_length: number;
  longest_length: number;
  status: "active" | "on_break" | "building";
  last_active_date: string;
  next_action_hint: string;
}

interface Challenge {
  challenge_id: string;
  date: string;
  type: string;
  prompt: string;
  status: string;
  next_action_hint: string;
}

interface MomentumData {
  score: number;
  trend: "up" | "flat" | "down";
  nextActionHint: string;
  computedAt: string;
}

interface CoachFeedback {
  suggestions: string[];
  summary: string;
}

interface Archetype {
  userId: string;
  primary: string;
  secondary: string | null;
  explanation: string[];
  updatedAt: string;
}

export default function TodayPage() {
  const { user, isLoaded } = useUser();
  const [streak, setStreak] = useState<StreakData | null>(null);
  const [challenge, setChallenge] = useState<Challenge | null>(null);
  const [momentum, setMomentum] = useState<MomentumData | null>(null);
  const [archetype, setArchetype] = useState<Archetype | null>(null);
  const [coachDraft, setCoachDraft] = useState("");
  const [coachFeedback, setCoachFeedback] = useState<CoachFeedback | null>(null);
  const [loading, setLoading] = useState(true);
  const [coachLoading, setCoachLoading] = useState(false);
  const [backendDown, setBackendDown] = useState(false);

  useEffect(() => {
    if (!isLoaded || !user?.id) return;

    const fetchTodayData = async () => {
      try {
        setBackendDown(false);
        const [streakRes, challengeRes, momentumRes, archetypeRes] =
          await Promise.all([
            fetch("/api/streaks/current", { cache: "no-store" }),
            fetch("/api/challenges/today", { cache: "no-store" }),
            fetch("/api/momentum/today", { cache: "no-store" }),
            fetch("/api/archetypes/me", { cache: "no-store" }),
          ]);

        if (streakRes.ok) setStreak(await streakRes.json());
        if (challengeRes.ok) setChallenge(await challengeRes.json());
        if (momentumRes.ok) {
          const data = await momentumRes.json();
          setMomentum(data.data || data);
        }
        if (archetypeRes.ok) {
          const data = await archetypeRes.json();
          setArchetype(data.data || data);
        }
      } catch (err) {
        console.error("[Today] fetch error:", err);
        setBackendDown(true);
      } finally {
        setLoading(false);
      }
    };

    fetchTodayData();
  }, [isLoaded, user?.id]);

  const handleCoachFeedback = async () => {
    if (!coachDraft.trim()) return;
    setCoachLoading(true);
    try {
      const res = await fetch("/api/coach/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ draft: coachDraft }),
      });
      if (res.ok) {
        const data = await res.json();
        setCoachFeedback(data.data || data);
      }
    } catch (err) {
      console.error("[Today] Coach feedback error:", err);
    } finally {
      setCoachLoading(false);
    }
  };

  const handleChallengeComplete = async () => {
    if (!challenge) return;
    try {
      const res = await fetch("/api/challenges/today/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge_id: challenge.challenge_id }),
      });
      if (res.ok) {
        const updated = await res.json();
        setChallenge(updated.data || updated);
      }
    } catch (err) {
      console.error("[Today] Challenge complete error:", err);
    }
  };

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-400 mx-auto mb-4" />
          <p className="text-gray-300">Loading your day...</p>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-white mb-4">Sign in to see today's ritual</h1>
          <Link href="/" className="text-purple-400 hover:text-purple-300 font-medium">
            ← Back home
          </Link>
        </div>
      </div>
    );
  }

  const trendEmoji = {
    up: "📈",
    flat: "➡️",
    down: "📉",
  };

  const statusEmoji = {
    active: "🔥",
    on_break: "🌱",
    building: "🏗️",
  };

  const archetypeEmojis: Record<string, string> = {
    truth_teller: "🎯",
    builder: "🔨",
    philosopher: "💭",
    connector: "🤝",
    firestarter: "🔥",
    storyteller: "📖",
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white">
      {/* Header */}
      <div className="border-b border-purple-500/20 bg-black/20 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 py-4 flex justify-between items-center">
          <h1 className="text-3xl font-black">What matters today</h1>
          <Link href="/dashboard" className="text-purple-400 hover:text-purple-300 font-medium">
            ← Back to dashboard
          </Link>
        </div>
      </div>

      {/* Backend Down Banner */}
      {backendDown && (
        <div className="bg-yellow-900/30 border-b border-yellow-500/30 px-4 py-3">
          <p className="text-sm text-yellow-200">
            Backend temporarily unavailable. Showing cached data.
          </p>
        </div>
      )}

      {/* Main Content */}
      <div className="max-w-5xl mx-auto px-4 py-8 space-y-6">
        {/* Streak Card */}
        {streak && (
          <div className="bg-gradient-to-br from-orange-600/20 to-orange-900/20 border border-orange-500/30 rounded-2xl p-8">
            <div className="flex items-center gap-4 mb-6">
              <span className="text-5xl">{statusEmoji[streak.status]}</span>
              <div>
                <h2 className="text-3xl font-black text-white">
                  {streak.current_length}
                </h2>
                <p className="text-sm text-orange-200">day streak</p>
              </div>
            </div>
            <div className="space-y-2 mb-4">
              <p className="text-white/90">
                <strong>Status:</strong> {streak.status.replace("_", " ")}
              </p>
              {streak.next_action_hint && (
                <p className="text-orange-200 italic">💡 {streak.next_action_hint}</p>
              )}
            </div>
            <div className="flex gap-3">
              <Link
                href="/dashboard"
                className="px-4 py-2 bg-orange-500 hover:bg-orange-600 rounded-lg font-medium text-sm"
              >
                Complete today's action
              </Link>
            </div>
          </div>
        )}

        {/* Challenge Card */}
        {challenge && (
          <div className="bg-gradient-to-br from-blue-600/20 to-blue-900/20 border border-blue-500/30 rounded-2xl p-8">
            <div className="flex items-center gap-4 mb-6">
              <span className="text-5xl">🎯</span>
              <div>
                <h2 className="text-2xl font-bold text-white">Today's Challenge</h2>
                <p className="text-sm text-blue-200">Type: {challenge.type}</p>
              </div>
            </div>
            <div className="space-y-4 mb-4">
              <p className="text-white/90">{challenge.prompt}</p>
              <p className="text-blue-200 italic">
                {challenge.next_action_hint || "Make it count."}
              </p>
            </div>
            <button
              onClick={handleChallengeComplete}
              disabled={challenge.status === "completed"}
              className={`px-4 py-2 rounded-lg font-medium text-sm ${
                challenge.status === "completed"
                  ? "bg-green-600 text-white cursor-default"
                  : "bg-blue-500 hover:bg-blue-600 text-white"
              }`}
            >
              {challenge.status === "completed" ? "✓ Completed" : "Mark Complete"}
            </button>
          </div>
        )}

        {/* Momentum Card */}
        {momentum && (
          <div className="bg-gradient-to-br from-pink-600/20 to-pink-900/20 border border-pink-500/30 rounded-2xl p-8">
            <div className="flex items-center gap-4 mb-6">
              <span className="text-5xl">{trendEmoji[momentum.trend]}</span>
              <div>
                <h2 className="text-3xl font-black text-white">{momentum.score}</h2>
                <p className="text-sm text-pink-200">momentum today</p>
              </div>
            </div>
            <div className="space-y-2 mb-4">
              <p className="text-white/90">
                Trend:{" "}
                <span className="capitalize font-semibold">
                  {momentum.trend === "up" && "Rising 📈"}
                  {momentum.trend === "flat" && "Stable ➡️"}
                  {momentum.trend === "down" && "Dipping 📉"}
                </span>
              </p>
              {momentum.nextActionHint && (
                <p className="text-pink-200 italic">💡 {momentum.nextActionHint}</p>
              )}
            </div>
          </div>
        )}

        {/* Coach Quick Check */}
        <div className="bg-gradient-to-br from-green-600/20 to-green-900/20 border border-green-500/30 rounded-2xl p-8">
          <div className="flex items-center gap-4 mb-6">
            <span className="text-5xl">💬</span>
            <h2 className="text-2xl font-bold text-white">Coach Quick Check</h2>
          </div>
          <div className="space-y-4">
            <textarea
              value={coachDraft}
              onChange={(e) => setCoachDraft(e.target.value)}
              placeholder="Paste a draft to get instant feedback..."
              className="w-full p-4 rounded-lg bg-white/5 border border-green-500/30 text-white placeholder-white/50 focus:outline-none focus:border-green-500 resize-none h-24"
            />
            <button
              onClick={handleCoachFeedback}
              disabled={coachLoading || !coachDraft.trim()}
              className="px-4 py-2 bg-green-500 hover:bg-green-600 disabled:bg-green-700 rounded-lg font-medium text-sm"
            >
              {coachLoading ? "Thinking..." : "Get Feedback"}
            </button>
            {coachFeedback && (
              <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
                <p className="text-sm text-green-200 mb-2">Coach says:</p>
                <ul className="space-y-1">
                  {coachFeedback.suggestions.map((s, i) => (
                    <li key={i} className="text-white/90 text-sm flex gap-2">
                      <span>•</span> {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Archetype Card */}
        {archetype && (
          <div className="bg-gradient-to-br from-purple-600/20 to-purple-900/20 border border-purple-500/30 rounded-2xl p-8">
            <div className="flex items-center gap-4 mb-6">
              <span className="text-5xl">
                {archetypeEmojis[archetype.primary] || "✨"}
              </span>
              <div>
                <h2 className="text-2xl font-bold text-white">
                  {archetype.primary.replace("_", " ")}
                  {archetype.secondary && (
                    <span className="text-lg font-normal text-white/70 ml-2">
                      / {archetype.secondary.replace("_", " ")}
                    </span>
                  )}
                </h2>
                <p className="text-sm text-purple-200">Your creative identity</p>
              </div>
            </div>
            <ul className="space-y-2 mb-4">
              {archetype.explanation.map((bullet, i) => (
                <li key={i} className="text-white/90 text-sm flex gap-2">
                  <span className="text-purple-300">•</span> {bullet}
                </li>
              ))}
            </ul>
            <p className="text-xs text-white/50 italic">
              Evolves as you create and engage
            </p>
          </div>
        )}

        {/* Call to Action */}
        <div className="bg-gradient-to-r from-purple-600/20 to-pink-600/20 border border-purple-500/30 rounded-2xl p-8 text-center">
          <h3 className="text-2xl font-bold text-white mb-3">
            Ready to show up?
          </h3>
          <p className="text-white/70 mb-6">
            Your streak, challenges, and momentum all compound with today's action.
          </p>
          <Link
            href="/dashboard"
            className="inline-block px-8 py-3 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 rounded-lg font-bold text-white"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
