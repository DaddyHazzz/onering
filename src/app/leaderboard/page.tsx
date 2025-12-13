"use client";

import { useEffect, useState } from "react";

export default function LeaderboardPage() {
  const [rows, setRows] = useState<Array<{user:string; ring:number}>>([]);

  useEffect(() => {
    setRows(
      Array.from({ length: 10 }).map((_, i) => ({ user: `user${i+1}`, ring: Math.floor(Math.random()*10000) }))
    );
  }, []);

  return (
    <main className="p-10 text-white">
      <h1 className="text-3xl font-bold mb-6">RING Leaderboard (mock)</h1>
      <table className="w-full">
        <thead>
          <tr className="border-b border-white/10"><th>#</th><th>User</th><th>RING</th></tr>
        </thead>
        <tbody>
          {rows.sort((a,b)=>b.ring-a.ring).map((r, idx) => (
            <tr key={r.user} className="border-b border-white/5"><td>{idx+1}</td><td>{r.user}</td><td>{r.ring}</td></tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
