"use client";

/**
 * src/app/u/[handle]/page.tsx
 * Public creator profile page
 * Shows streak, momentum, recent posts
 * No auth required (read-only public data)
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { useUser } from "@clerk/nextjs";

interface ProfileData {
  user_id: string;
  display_name: string;
  streak: {
    current_length: number;
    longest_length: number;
    status: "active" | "on_break" | "building";
    last_active_date: string;
  };
  momentum_today: {
    score: number;
    trend: "up" | "flat" | "down";
    components: {
      streakComponent: number;
      consistencyComponent: number;
      challengeComponent: number;
      coachComponent: number;
    };
    nextActionHint: string;
    computedAt: string;
  };
  momentum_weekly: Array<{
    score: number;
    trend: "up" | "flat" | "down";
    components: any;
    nextActionHint: string;
    computedAt: string;
  }>;
  recent_posts: Array<{
    id: string;
    platform: string;
    content: string;
    created_at: string;
  }>;
  profile_summary: string;
  computed_at: string;
  archetype?: {
    userId: string;
    primary: string;
    secondary: string | null;
    explanation: string[];
    updatedAt: string;
  };
}

interface PageProps {
  params: {
    handle: string;
  };
}

export default function PublicProfilePage({ params }: PageProps) {
  const { user: currentUser, isLoaded } = useUser();
  const [profile, setProfile] = useState<ProfileData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { handle } = params;

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setLoading(true);
        const res = await fetch(`/api/profile/public?handle=${encodeURIComponent(handle)}`);
        
        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.error || "Failed to load profile");
        }

        const data = await res.json();
        setProfile(data.data);
      } catch (err: any) {
        setError(err.message || "Error loading profile");
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [handle]);

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-400 mx-auto mb-4" />
          <p className="text-gray-300">Loading profile...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !profile) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">😕</div>
          <h1 className="text-2xl font-bold text-white mb-2">Profile Not Found</h1>
          <p className="text-gray-400 mb-6">
            {error || `Could not load the profile for @${handle}`}
          </p>
          <Link href="/dashboard" className="text-purple-400 hover:text-purple-300 font-medium">
            ← Back to Dashboard
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Header */}
      <div className="border-b border-purple-500/20 bg-black/20 backdrop-blur">
        <div className="max-w-4xl mx-auto px-4 py-4 flex justify-between items-center">
          <Link href="/dashboard" className="text-gray-400 hover:text-gray-300 font-medium">
            ← Dashboard
          </Link>
          {isLoaded && currentUser && currentUser.username === handle ? (
            <Link href="/dashboard" className="text-purple-400 hover:text-purple-300 font-medium">
              Edit Profile →
            </Link>
          ) : null}
        </div>
      </div>

      {/* Profile Header */}
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <h1 className="text-5xl font-black text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-pink-400 mb-2">
          @{handle}
        </h1>
        <p className="text-gray-300 text-lg mb-6">{profile.display_name}</p>
        <p className="text-gray-400 italic max-w-2xl mx-auto mb-8">"{profile.profile_summary}"</p>
      </div>

      {/* Main Grid */}
      <div className="max-w-4xl mx-auto px-4 pb-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Archetype Card (if available) */}
          {profile.archetype && (
            <div className="md:col-span-2 bg-gradient-to-br from-indigo-600/20 to-purple-900/20 border border-indigo-500/30 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <span className="text-4xl">
                  {
                    {
                      truth_teller: "🎯",
                      builder: "🔨",
                      philosopher: "💭",
                      connector: "🤝",
                      firestarter: "🔥",
                      storyteller: "📖",
                    }[profile.archetype.primary] || "✨"
                  }
                </span>
                <div>
                  <h2 className="text-2xl font-bold text-white">
                    {
                      {
                        truth_teller: "Truth Teller",
                        builder: "Builder",
                        philosopher: "Philosopher",
                        connector: "Connector",
                        firestarter: "Firestarter",
                        storyteller: "Storyteller",
                      }[profile.archetype.primary] || profile.archetype.primary
                    }
                    {profile.archetype.secondary && (
                      <span className="text-lg font-normal text-white/70 ml-2">
                        /{" "}
                        {
                          {
                            truth_teller: "Truth Teller",
                            builder: "Builder",
                            philosopher: "Philosopher",
                            connector: "Connector",
                            firestarter: "Firestarter",
                            storyteller: "Storyteller",
                          }[profile.archetype.secondary] || profile.archetype.secondary
                        }
                      </span>
                    )}
                  </h2>
                  <p className="text-sm text-gray-400">Creative Archetype</p>
                </div>
              </div>
              <ul className="space-y-2 mb-2">
                {profile.archetype.explanation.map((bullet, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-gray-300 text-sm">
                    <span className="text-purple-400 mt-0.5">•</span>
                    <span>{bullet}</span>
                  </li>
                ))}
              </ul>
              <p className="text-xs text-gray-500 italic">
                Evolves over time based on content and engagement.
              </p>
            </div>
          )}

          {/* Streak Card */}
          <div className="bg-gradient-to-br from-purple-600/20 to-purple-900/20 border border-purple-500/30 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white">Streak</h2>
              <span className="text-2xl">{statusEmoji[profile.streak.status]}</span>
            </div>
            <div className="space-y-3">
              <div>
                <p className="text-gray-400 text-sm mb-1">Current</p>
                <p className="text-4xl font-black text-purple-300">
                  {profile.streak.current_length}
                </p>
                <p className="text-xs text-gray-500 mt-1">days</p>
              </div>
              <div>
                <p className="text-gray-400 text-sm mb-1">Personal Best</p>
                <p className="text-2xl font-bold text-gray-300">
                  {profile.streak.longest_length}
                </p>
              </div>
              <div className="pt-3 border-t border-purple-500/20">
                <p className="text-gray-400 text-sm mb-1">Status</p>
                <p className="text-white font-medium capitalize">
                  {profile.streak.status.replace("_", " ")}
                </p>
              </div>
            </div>
          </div>

          {/* Momentum Card */}
          <div className="bg-gradient-to-br from-pink-600/20 to-pink-900/20 border border-pink-500/30 rounded-lg p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-white">Momentum Today</h2>
              <span className="text-2xl">{trendEmoji[profile.momentum_today.trend]}</span>
            </div>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between items-end mb-2">
                  <p className="text-gray-400 text-sm">Score</p>
                  <p className="text-3xl font-black text-pink-300">
                    {Math.round(profile.momentum_today.score)}
                  </p>
                </div>
                <div className="w-full bg-gray-700 rounded-full h-2">
                  <div
                    className="bg-gradient-to-r from-pink-500 to-purple-500 h-2 rounded-full"
                    style={{ width: `${profile.momentum_today.score}%` }}
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-3 border-t border-pink-500/20">
                <div>
                  <p className="text-gray-400 text-xs">Streak</p>
                  <p className="text-sm font-bold text-white">
                    {Math.round(profile.momentum_today.components.streakComponent)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 text-xs">Consistency</p>
                  <p className="text-sm font-bold text-white">
                    {Math.round(profile.momentum_today.components.consistencyComponent)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 text-xs">Challenge</p>
                  <p className="text-sm font-bold text-white">
                    {Math.round(profile.momentum_today.components.challengeComponent)}
                  </p>
                </div>
                <div>
                  <p className="text-gray-400 text-xs">Coach</p>
                  <p className="text-sm font-bold text-white">
                    {Math.round(profile.momentum_today.components.coachComponent)}
                  </p>
                </div>
              </div>
              <div className="pt-3 border-t border-pink-500/20">
                <p className="text-xs text-gray-500 mb-1">Next Action</p>
                <p className="text-sm text-white italic">"{profile.momentum_today.nextActionHint}"</p>
              </div>
            </div>
          </div>
        </div>

        {/* Weekly Momentum */}
        <div className="mt-6 bg-gradient-to-br from-amber-600/20 to-amber-900/20 border border-amber-500/30 rounded-lg p-6">
          <h2 className="text-lg font-bold text-white mb-4">7-Day Momentum</h2>
          <div className="grid grid-cols-7 gap-2">
            {profile.momentum_weekly.map((day, idx) => (
              <div key={idx} className="text-center">
                <div className="text-xs text-gray-400 mb-2">
                  {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][idx]}
                </div>
                <div className="bg-gray-700 rounded-lg p-2 mb-1">
                  <p className="text-lg font-bold text-amber-300">
                    {Math.round(day.score)}
                  </p>
                </div>
                <span className="text-sm">{trendEmoji[day.trend]}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Recent Posts */}
        {profile.recent_posts.length > 0 && (
          <div className="mt-6 bg-gradient-to-br from-blue-600/20 to-blue-900/20 border border-blue-500/30 rounded-lg p-6">
            <h2 className="text-lg font-bold text-white mb-4">Recent Posts</h2>
            <div className="space-y-3">
              {profile.recent_posts.map((post) => (
                <div key={post.id} className="bg-black/20 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-xs font-bold text-blue-300 uppercase">
                      {post.platform}
                    </span>
                    <span className="text-xs text-gray-500">
                      {new Date(post.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  <p className="text-white text-sm line-clamp-2">{post.content}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Share Button */}
        <div className="mt-8 text-center">
          <button
            onClick={() => {
              const url = `${window.location.origin}/u/${handle}`;
              navigator.clipboard.writeText(url);
              alert("Profile link copied to clipboard!");
            }}
            className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold rounded-lg hover:shadow-lg transition"
          >
            📋 Share Profile
          </button>
        </div>
      </div>
    </div>
  );
}
