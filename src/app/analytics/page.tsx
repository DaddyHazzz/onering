"use client";

import { useUser } from "@clerk/nextjs";
import { useEffect, useState } from "react";
import LeaderboardPanel from "@/components/analytics/LeaderboardPanel";

export default function AnalyticsPage() {
  const { user } = useUser();
  const [rows, setRows] = useState<Array<any>>([]);
  const [stats, setStats] = useState<Array<any>>([]);

  useEffect(() => {
    // Mock data
    setRows(
      Array.from({ length: 10 }).map((_, i) => ({
        id: i + 1,
        title: `Mock Post #${i + 1}`,
        views: Math.floor(Math.random() * 5000),
        likes: Math.floor(Math.random() * 1000),
      }))
    );
    // fetch viewership for current user
    (async () => {
      try {
        const res = await fetch('/api/viewership');
        const d = await res.json();
        if (d.success) setStats(d.stats);
      } catch (e) {
        console.error('viewership fetch failed', e);
      }
    })();
  }, []);

  if (!user) return <div className="p-10 text-white">Sign in to view analytics.</div>;

  return (
    <main className="p-10 min-h-screen bg-gray-900">
      <h1 className="text-3xl font-bold mb-6">Analytics (mock)</h1>
      
      {/* Community Leaderboard Section */}
      <div className="mb-8">
        <LeaderboardPanel />
      </div>
      
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className="border-b border-white/10">
            <th className="py-2">#</th>
            <th>Title</th>
            <th>Views</th>
            <th>Likes</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => {
            const s = stats[idx] || { views: r.views, likes: r.likes };
            return (
              <tr key={r.id} className="border-b border-white/5">
                <td className="py-3">{r.id}</td>
                <td>{r.title}</td>
                <td>{s.views}</td>
                <td>{s.likes}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </main>
  );
}
