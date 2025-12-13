"use client";

import Link from "next/link";
import { useState } from "react";

export default function Home() {
  const [email, setEmail] = useState("");

  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-black text-white p-8">
      <div className="max-w-4xl text-center">
        <h1 className="mb-4 text-center text-6xl font-black tracking-tighter md:text-8xl">
          OneRing
        </h1>
        <p className="mb-6 text-2xl opacity-80">Built by a felon. Powered by Grok. Verified by you.</p>

        <div className="mb-8">
          <iframe title="viral-thread" src="about:blank" className="w-full h-48 bg-white/5 rounded mb-4" />
          <div className="flex items-center justify-center gap-4">
            <Link href="/sign-up" className="rounded-full bg-purple-600 px-8 py-3 text-lg font-bold">Start for free</Link>
            <Link href="/sign-in" className="rounded-full border-2 border-white px-8 py-3 text-lg font-bold">Sign in</Link>
          </div>
        </div>

        <div className="bg-white/5 p-6 rounded">
          <h3 className="text-xl font-bold mb-2">Join the waitlist</h3>
          <p className="mb-4 opacity-80">Drop your email to get early access and product updates.</p>
          <div className="flex gap-2">
            <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@internet.com" className="p-3 rounded flex-1 bg-black/20" />
            <button onClick={() => alert(`Thanks — mock saved ${email}`)} className="px-4 py-3 bg-purple-600 rounded">Join</button>
          </div>
        </div>

        <div className="mt-8 p-6 bg-white/5 rounded">
          <h2 className="text-2xl font-bold mb-2">The OneRing — coming 2026</h2>
          <p className="opacity-80 mb-4">Records life. Posts hands-free. Earns RING while you sleep.</p>
          <div className="flex items-center justify-center">
            <div className="w-40 h-40 bg-yellow-400 rounded-full flex items-center justify-center text-black font-black text-3xl shadow-lg">RING</div>
          </div>
        </div>
      </div>
    </main>
  );
}