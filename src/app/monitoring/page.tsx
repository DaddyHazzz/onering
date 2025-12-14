"use client";

import { useEffect, useState } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

interface SystemStats {
  activeUsers: number;
  totalRingCirculated: number;
  postSuccessRate: number;
  totalPostsPublished: number;
  totalPostsFailed: number;
  avgPostEarnings: number;
}

interface AgentTrace {
  workflowId: string;
  topic: string;
  status: "generating" | "optimizing" | "posting" | "completed" | "failed";
  startTime: string;
  duration?: number;
}

export default function MonitoringPage() {
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [traces, setTraces] = useState<AgentTrace[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is admin (this is a stub - in production, check Clerk roles)
    if (isLoaded && user) {
      // For now, allow any authenticated user to view monitoring
      // In production: const isAdmin = user.publicMetadata?.role === 'admin'
      fetchStats();
      const interval = setInterval(fetchStats, 5000); // Refresh every 5s
      return () => clearInterval(interval);
    } else if (isLoaded && !user) {
      router.push("/");
    }
  }, [isLoaded, user, router]);

  const fetchStats = async () => {
    try {
      const res = await fetch("/api/monitoring/stats");
      const data = await res.json();
      if (res.ok) {
        setStats(data);
      }
    } catch (error) {
      console.error("[monitoring] error fetching stats:", error);
    }
    setLoading(false);
  };

  if (!isLoaded || loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 text-white flex items-center justify-center">
        <div className="text-2xl font-bold">Loading monitoring dashboard...</div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 text-white p-10">
      <div className="max-w-7xl mx-auto">
        <div className="mb-12">
          <h1 className="text-6xl font-black mb-2">Monitoring Dashboard</h1>
          <p className="text-xl text-gray-400">OneRing System Health & Analytics</p>
        </div>

        {/* System Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {/* Active Users */}
          <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-8 shadow-xl border border-white/20">
            <div className="text-5xl font-black text-purple-400 mb-3">
              {stats?.activeUsers || 0}
            </div>
            <p className="text-lg font-semibold text-gray-300">Active Users (24h)</p>
            <p className="text-sm text-gray-500 mt-2">Unique users who posted or generated content</p>
          </div>

          {/* Total RING Circulated */}
          <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-8 shadow-xl border border-white/20">
            <div className="text-5xl font-black text-yellow-400 mb-3">
              {(stats?.totalRingCirculated || 0).toLocaleString()}
            </div>
            <p className="text-lg font-semibold text-gray-300">RING Circulated</p>
            <p className="text-sm text-gray-500 mt-2">Total RING earned by users</p>
          </div>

          {/* Post Success Rate */}
          <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-8 shadow-xl border border-white/20">
            <div className="text-5xl font-black text-green-400 mb-3">
              {((stats?.postSuccessRate || 0) * 100).toFixed(1)}%
            </div>
            <p className="text-lg font-semibold text-gray-300">Post Success Rate</p>
            <p className="text-sm text-gray-500 mt-2">Successful posts / total attempts</p>
          </div>

          {/* Total Posts */}
          <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-8 shadow-xl border border-white/20">
            <div className="text-5xl font-black text-blue-400 mb-3">
              {stats?.totalPostsPublished || 0}
            </div>
            <p className="text-lg font-semibold text-gray-300">Posts Published</p>
            <p className="text-sm text-gray-500 mt-2">Across all platforms (X, IG, etc.)</p>
          </div>

          {/* Failed Posts */}
          <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-8 shadow-xl border border-white/20">
            <div className="text-5xl font-black text-red-400 mb-3">
              {stats?.totalPostsFailed || 0}
            </div>
            <p className="text-lg font-semibold text-gray-300">Posts Failed</p>
            <p className="text-sm text-gray-500 mt-2">Scheduled/attempted posts that failed</p>
          </div>

          {/* Avg Earnings Per Post */}
          <div className="bg-white/10 backdrop-blur-xl rounded-2xl p-8 shadow-xl border border-white/20">
            <div className="text-5xl font-black text-pink-400 mb-3">
              {(stats?.avgPostEarnings || 0).toFixed(1)}
            </div>
            <p className="text-lg font-semibold text-gray-300">Avg RING/Post</p>
            <p className="text-sm text-gray-500 mt-2">Average earnings per post</p>
          </div>
        </div>

        {/* Recent Agent Traces */}
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-10 shadow-2xl border border-white/20">
          <h2 className="text-3xl font-bold mb-8">Recent Agent Workflows</h2>

          {traces.length === 0 ? (
            <div className="text-gray-400 text-lg py-12 text-center">
              No recent agent traces. Workflows will appear here as they execute.
            </div>
          ) : (
            <div className="space-y-4">
              {traces.map((trace) => (
                <div
                  key={trace.workflowId}
                  className="p-6 bg-black/40 rounded-xl border border-white/10 hover:border-white/30 transition"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex-1">
                      <p className="text-lg font-semibold">{trace.topic.slice(0, 50)}</p>
                      <p className="text-sm text-gray-500">ID: {trace.workflowId.slice(0, 12)}...</p>
                    </div>
                    <div className={`px-4 py-2 rounded-lg font-semibold text-sm ${
                      trace.status === "completed"
                        ? "bg-green-500/30 text-green-300"
                        : trace.status === "failed"
                        ? "bg-red-500/30 text-red-300"
                        : "bg-blue-500/30 text-blue-300"
                    }`}>
                      {trace.status.toUpperCase()}
                    </div>
                  </div>
                  <div className="flex items-center justify-between text-sm text-gray-400">
                    <span>Started: {new Date(trace.startTime).toLocaleTimeString()}</span>
                    {trace.duration && <span>Duration: {trace.duration}ms</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>Dashboard auto-refreshes every 5 seconds</p>
          <p>Last updated: {new Date().toLocaleTimeString()}</p>
        </div>
      </div>
    </div>
  );
}
