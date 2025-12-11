"use client";

import { UserButton, useUser } from "@clerk/nextjs";
import { useState } from "react";
import { loadStripe, Stripe } from "@stripe/stripe-js";

// Load Stripe with correct NEXT_PUBLIC variable
const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || ""
);

export default function Dashboard() {
  const { user } = useUser();
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setResult("");

    const res = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });

    const data = await res.json();
    setResult(data.content || data.error || "Something went wrong.");
    setLoading(false);
  };

  const startCheckout = async () => {
    const stripe: Stripe | null = await stripePromise;

    if (!stripe) {
      console.error("Stripe failed to load.");
      return alert("Stripe didn't load — check NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY.");
    }

    const res = await fetch("/api/stripe/checkout", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId: user?.id }),
    });

    const { sessionId } = await res.json();

    if (!sessionId) {
      console.error("No sessionId from backend");
      return alert("Stripe sessionId missing — check backend route.");
    }

    const { error } = await stripe.redirectToCheckout({ sessionId });

    if (error) {
      console.error(error);
      alert(error.message);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 text-white p-10">
      <div className="max-w-5xl mx-auto">
        <div className="flex justify-between items-center mb-16">
          <h1 className="text-6xl font-black">OneRing</h1>
          <UserButton afterSignOutUrl="/" />
        </div>

        {/* === BLUE CHECK BUTTON === */}
        {!user?.publicMetadata?.verified && (
          <div className="text-center my-16">
            <button
              onClick={startCheckout}
              className="px-20 py-10 bg-gradient-to-r from-yellow-400 to-yellow-600 hover:from-yellow-500 hover:to-yellow-700 rounded-3xl text-5xl font-black text-black shadow-2xl transform hover:scale-110 transition duration-300"
            >
              Get Verified Blue Check ($99/year)
            </button>
          </div>
        )}

        {user?.publicMetadata?.verified && (
          <div className="text-center my-12">
            <span className="inline-flex items-center gap-4 text-6xl font-bold">
              Verified
              <svg className="w-16 h-16 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M22.5 12.5l-9.99 10-6.01-6 1.42-1.42L12.5 19.66l8.58-8.58z" />
              </svg>
            </span>
          </div>
        )}

        {/* === GENERATE POST SECTION === */}
        <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-10 shadow-2xl">
          <h2 className="text-4xl font-bold mb-8">Generate Your Next Viral Post</h2>

          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g. I’m a felon who built a SaaS from a halfway house…"
            className="w-full h-32 p-6 rounded-2xl bg-white/5 border border-white/20 text-white placeholder-white/50 text-xl focus:outline-none focus:border-purple-500 resize-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                generate();
              }
            }}
          />

          <button
            onClick={generate}
            disabled={loading || !prompt.trim()}
            className="mt-8 px-12 py-6 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 rounded-2xl text-2xl font-bold transition transform hover:scale-105"
          >
            {loading ? "Grok is cooking..." : "Generate with Grok"}
          </button>

          {result && (
            <div className="mt-12 p-8 bg-black/40 rounded-2xl whitespace-pre-wrap text-xl leading-relaxed border border-purple-500">
              <strong>Generated Post:</strong>
              <pre className="mt-4 whitespace-pre-wrap font-sans">{result}</pre>

              <div className="mt-6 flex flex-wrap gap-4">
                <button
                  onClick={async () => {
                    setLoading(true);
                    const res = await fetch("/api/post-to-x", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ content: result }),
                    });
                    const data = await res.json();
                    setLoading(false);
                    alert(data.success ? `Posted! ${data.url}` : `Error: ${data.error}`);
                  }}
                  disabled={loading}
                  className="px-10 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-xl text-2xl font-black"
                >
                  {loading ? "Posting..." : "Post to X Now"}
                </button>

                <button
                  onClick={() => navigator.clipboard.writeText(result)}
                  className="px-8 py-4 bg-gray-700 hover:bg-gray-600 rounded-xl text-xl font-bold"
                >
                  Copy Thread
                </button>
              </div>
            </div>
          )}
        </div>

        <p className="text-center mt-20 text-xl opacity-70">
          Welcome back, {user?.firstName || "King"}
        </p>
      </div>
    </div>
  );
}
