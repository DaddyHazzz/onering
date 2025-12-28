"use client";

import { UserButton, useUser } from "@clerk/nextjs";
import { useState, useEffect } from "react";
import { loadStripe } from "@stripe/stripe-js";
import ArchetypeCard from "@/components/ArchetypeCard";
import EnforcementBadge from "@/components/EnforcementBadge";
import EnforcementErrorCallout from "@/components/EnforcementErrorCallout";
import TokenResultCallout from "@/components/TokenResultCallout";
import {
  buildEnforcementRequestFields,
  EnforcementPayload,
  normalizeEnforcementPayload,
  parseSseEvents,
} from "@/lib/enforcement";

// Make sure this is the publishable key (the pk_test_ one)
const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!
);

interface UserPublicMetadata {
  verified?: boolean;
}

interface FamilyMember {
  id: string;
  name: string;
  ringBalance: number;
  verified: boolean;
}

interface TokenResult {
  mode: string;
  issued_amount?: number;
  pending_amount?: number;
  reason_code?: string;
  guardrails_applied?: string[];
}

interface LedgerEntry {
  id: string;
  eventType: string;
  reasonCode: string;
  amount: number;
  balanceAfter: number;
  createdAt?: string | null;
}

interface TokenSummary {
  mode: string;
  balance: number;
  pending_total: number;
  effective_balance: number;
  last_ledger_at?: string | null;
  last_pending_at?: string | null;
}

export default function Dashboard() {
  const { user } = useUser();
  const [prompt, setPrompt] = useState("");
  const [result, setResult] = useState("");
  const [loading, setLoading] = useState(false);
  const [ring, setRing] = useState<number>(0);
  const [history, setHistory] = useState<Array<{platform:string; content:string; time:string}>>([]);
  const [refCode, setRefCode] = useState<string | null>(null);
  const [claimInput, setClaimInput] = useState('');
  const [promoInput, setPromoInput] = useState('');
  const [familyMembers, setFamilyMembers] = useState<FamilyMember[]>([]);
  const [combinedRingBalance, setCombinedRingBalance] = useState<number>(0);
  const [newMemberName, setNewMemberName] = useState("");
  const [loadingFamily, setLoadingFamily] = useState(false);
  const [topicForThread, setTopicForThread] = useState("");
  const [threadLines, setThreadLines] = useState<string[]>([]);
  const [loadingThread, setLoadingThread] = useState(false);
  const [enforcementSimple, setEnforcementSimple] = useState<EnforcementPayload | null>(null);
  const [enforcementThread, setEnforcementThread] = useState<EnforcementPayload | null>(null);
  const [postError, setPostError] = useState<{ message?: string; suggestedFix?: string } | null>(null);
  const [threadPostError, setThreadPostError] = useState<{ message?: string; suggestedFix?: string } | null>(null);
  const [streak, setStreak] = useState<{ current_length: number; longest_length: number; status: string; next_action_hint: string } | null>(null);
  const [loadingStreak, setLoadingStreak] = useState(false);
  const [challenge, setChallenge] = useState<{ challenge_id: string; date: string; type: string; prompt: string; status: string; next_action_hint: string } | null>(null);
  const [loadingChallenge, setLoadingChallenge] = useState(false);
  const [tokenResult, setTokenResult] = useState<TokenResult | null>(null);
  const [tokenBalance, setTokenBalance] = useState<number | null>(null);
  const [tokenPending, setTokenPending] = useState<number>(0);
  const [tokenLedger, setTokenLedger] = useState<LedgerEntry[]>([]);
  const [tokenSummary, setTokenSummary] = useState<TokenSummary | null>(null);
  const isAdmin = Boolean((user?.publicMetadata as any)?.isAdmin || (user?.publicMetadata as any)?.role === "admin");

  const refreshStreak = async () => {
    if (!user?.id) return;
    setLoadingStreak(true);
    try {
      const res = await fetch("/api/streaks/current", { cache: "no-store" });
      const data = await res.json();
      if (res.ok) {
        setStreak(data);
      }
    } catch (err) {
      console.error("[dashboard] streak fetch failed", err);
    } finally {
      setLoadingStreak(false);
    }
  };

  const refreshChallenge = async () => {
    if (!user?.id) return;
    setLoadingChallenge(true);
    try {
      const res = await fetch("/api/challenges/today", { cache: "no-store" });
      const data = await res.json();
      if (res.ok) {
        setChallenge(data);
      }
    } catch (err) {
      console.error("[dashboard] challenge fetch failed", err);
    } finally {
      setLoadingChallenge(false);
    }
  };

  const handleAcceptChallenge = async () => {
    if (!challenge) return;
    setLoadingChallenge(true);
    try {
      const res = await fetch("/api/challenges/today/accept", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge_id: challenge.challenge_id }),
      });
      const data = await res.json();
      if (res.ok) {
        await refreshChallenge();
      } else {
        alert(data.error || "Failed to accept challenge");
      }
    } catch (err) {
      console.error("[dashboard] accept challenge failed", err);
      alert("Failed to accept challenge");
    } finally {
      setLoadingChallenge(false);
    }
  };

  const handleCompleteChallenge = async () => {
    if (!challenge) return;
    setLoadingChallenge(true);
    try {
      const res = await fetch("/api/challenges/today/complete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge_id: challenge.challenge_id }),
      });
      const data = await res.json();
      if (res.ok) {
        await refreshChallenge();
        await refreshStreak(); // Refresh streak in case it was incremented
        alert(data.next_action_hint || "Challenge completed!");
      } else {
        alert(data.error || "Failed to complete challenge");
      }
    } catch (err) {
      console.error("[dashboard] complete challenge failed", err);
      alert("Failed to complete challenge");
    } finally {
      setLoadingChallenge(false);
    }
  };

  const protectionStride = 7;
  const streakLength = streak?.current_length ?? 0;
  const strideProgressRaw = streakLength === 0 ? 0 : streakLength % protectionStride || protectionStride;
  const strideProgress = Math.min(1, strideProgressRaw / protectionStride);

  useEffect(() => {
    // initialize ring from Clerk metadata (history only; balance uses token summary)
    const meta = (user?.publicMetadata as any) || {};
    setHistory(Array.isArray(meta.posts) ? meta.posts.slice(0,5) : []);
  }, [user?.id]); // Depend on user.id instead of user.publicMetadata to avoid re-renders

  // Load family members
  useEffect(() => {
    const loadFamily = async () => {
      try {
        const res = await fetch("/api/family/list");
        const data = await res.json();
        setFamilyMembers(data.familyMembers || []);
        setCombinedRingBalance(data.combinedRingBalance || 0);
      } catch (e) {
        console.error("Failed to load family members:", e);
      }
    };
    loadFamily();
  }, [user?.id]);

  const refreshTokenLedger = async () => {
    try {
      const [balanceRes, ledgerRes] = await Promise.all([
        fetch("/api/tokens/summary", { cache: "no-store" }),
        fetch("/api/tokens/ledger?limit=20", { cache: "no-store" }),
      ]);
      const balanceData = await balanceRes.json();
      const ledgerData = await ledgerRes.json();
      if (balanceRes.ok) {
        setTokenBalance(balanceData.balance ?? null);
        setTokenPending(balanceData.pending_total ?? 0);
        setTokenSummary(balanceData);
        setRing(balanceData.effective_balance ?? balanceData.balance ?? 0);
      }
      if (ledgerRes.ok) {
        setTokenLedger(ledgerData.entries || []);
      }
    } catch (err) {
      console.error("[dashboard] token ledger fetch failed", err);
    }
  };

  // Claim daily login bonus on component mount
  useEffect(() => {
    const claimDailyBonus = async () => {
      try {
        const res = await fetch("/api/ring/daily-login", { method: "POST" });
        const data = await res.json();
        if (data.success) {
          await refreshTokenLedger();
          console.log("[dashboard] daily login bonus:", data.message);
        }
      } catch (e) {
        console.error("Failed to claim daily bonus:", e);
      }
    };
    if (user?.id) {
      claimDailyBonus();
    }
  }, [user?.id]);

  useEffect(() => {
    if (user?.id) {
      refreshStreak();
    }
  }, [user?.id]);

  useEffect(() => {
    if (user?.id) {
      refreshChallenge();
    }
  }, [user?.id]);

  useEffect(() => {
    if (user?.id) {
      refreshTokenLedger();
    }
  }, [user?.id]);

  // show success toast if returned from Stripe checkout
  useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      if (params.get('session_id')) {
        // optimistically show toast and remove param
        alert('Verified! Blue check earned — +500 RING');
        const url = new URL(window.location.href);
        url.searchParams.delete('session_id');
        window.history.replaceState({}, '', url.toString());
      }
    } catch (e) {
      // ignore when server-rendering
    }
  }, []);

  const generate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setResult("");
    setEnforcementSimple(null);
    setPostError(null);

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt,
          type: "simple",
          platform: "x",
          user_id: user?.id || "anon",
          stream: true,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        setResult(errorData.error || "Generation failed");
        setLoading(false);
        return;
      }

      // Handle streaming response
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) {
        setResult("No response from server");
        setLoading(false);
        return;
      }

      let fullContent = "";
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parsed = parseSseEvents(buffer);
        buffer = parsed.rest;

        for (const event of parsed.events) {
          if (event.event === "enforcement") {
            try {
              const payload = normalizeEnforcementPayload(JSON.parse(event.data));
              if (payload) setEnforcementSimple(payload);
            } catch (err) {
              console.error("[generate] failed to parse enforcement payload", err);
            }
            continue;
          }

          const token = event.data.trim();
          if (token && token !== "[DONE]") {
            fullContent += token;
            setResult(fullContent);
          }
        }
      }
      
      setLoading(false);
    } catch (error: any) {
      console.error("[generate] error:", error);
      setResult(`Error: ${error.message}`);
      setLoading(false);
    }
  };

  const generateViralThread = async () => {
    if (!topicForThread.trim()) return;
    setLoadingThread(true);
    setThreadLines([]);
    setEnforcementThread(null);
    setThreadPostError(null);

    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt: topicForThread,
          type: "viral_thread",
          platform: "x",
          user_id: user?.id || "anon",
          stream: true,
        }),
      });

      if (!res.ok) {
        alert("Failed to generate thread");
        setLoadingThread(false);
        return;
      }

      // Stream response as SSE
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) {
        setLoadingThread(false);
        return;
      }

      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parsed = parseSseEvents(buffer);
        buffer = parsed.rest;

        for (const event of parsed.events) {
          if (event.event === "enforcement") {
            try {
              const payload = normalizeEnforcementPayload(JSON.parse(event.data));
              if (payload) setEnforcementThread(payload);
            } catch (err) {
              console.error("[thread] failed to parse enforcement payload", err);
            }
            continue;
          }
          const threadLine = event.data.trim();
          if (threadLine) {
            setThreadLines((prev) => [...prev, threadLine]);
          }
        }
      }

      setLoadingThread(false);
    } catch (error) {
      console.error("Thread generation error:", error);
      alert("Error generating thread");
      setLoadingThread(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 text-white p-10">
      <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-6">
                <h1 className="text-6xl font-black">OneRing</h1>
                <div className="ml-4 px-4 py-2 bg-yellow-300 text-black rounded-lg font-bold">RING: {ring}</div>
                {tokenSummary?.mode && tokenSummary.mode !== "off" && (
                  <span className="px-2 py-1 rounded-full text-xs bg-emerald-500/20 text-emerald-200 border border-emerald-400/40">
                    ledger-truth
                  </span>
                )}
                {tokenSummary?.pending_total ? (
                  <span className="px-2 py-1 rounded-full text-xs bg-yellow-500/20 text-yellow-200 border border-yellow-400/40">
                    pending {tokenSummary.pending_total}
                  </span>
                ) : null}
                {streak && (
                  <div className="ml-2 px-4 py-2 bg-orange-400 text-black rounded-lg font-bold">
                    🔥 {streak.current_length} day streak
                  </div>
                )}
              </div>
            <div className="flex items-center gap-4">
              <button onClick={async () => {
                try {
                  const res = await fetch('/api/mine-ring', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ amount: 100 }) });
                  const d = await res.json();
                  if (!res.ok) return alert(d.error || 'mine failed');
                  await refreshTokenLedger();
                  alert('Mined +100 RING');
                } catch (e) { console.error(e); alert('mine failed'); }
              }} className="px-3 py-2 bg-yellow-500 text-black rounded">Mine RING +100</button>
              <UserButton afterSignOutUrl="/" />
            </div>
          </div>

        <TokenResultCallout tokenResult={tokenResult} />

        {/* ==== ARCHETYPE CARD ==== */}
        <div className="mb-8">
          <ArchetypeCard />
        </div>

        {/* ==== BLUE CHECK BUTTON ==== */}
        {!(user?.publicMetadata as UserPublicMetadata)?.verified && (
          <div className="text-center my-16">
            <button
              onClick={async () => {
                try {
                  const res = await fetch('/api/stripe/checkout');
                  const data = await res.json();
                  if (data.error) return alert(`Stripe error: ${data.error}`);
                  const sessionUrl = data.sessionUrl;
                  if (!sessionUrl) return alert('No session url returned');
                  alert('Redirecting to pay for your crown...');
                  window.location.href = sessionUrl;
                } catch (err: any) {
                  console.error("checkout click error:", err);
                  alert(err?.message || String(err));
                }
              }}
              className="px-20 py-10 bg-gradient-to-r from-yellow-400 to-yellow-600 hover:from-yellow-500 hover:to-yellow-700 rounded-3xl text-5xl font-black text-black shadow-2xl transform hover:scale-110 transition duration-300"
            >
              Get Verified Blue Check ($99/year)
            </button>
          </div>
        )}

        {((user?.publicMetadata as UserPublicMetadata)?.verified) && (
          <div className="text-center my-12">
            <span className="inline-flex items-center gap-4 text-6xl font-bold">
              Verified
              <svg className="w-16 h-16 text-blue-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M22.5 12.5l-9.99 10-6.01-6 1.42-1.42L12.5 19.66l8.58-8.58z" />
              </svg>
            </span>
          </div>
        )}

        {/* ==== GENERATE POST SECTION ==== */}
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
              <EnforcementBadge enforcement={enforcementSimple} />
              <EnforcementErrorCallout
                message={postError?.message}
                suggestedFix={postError?.suggestedFix}
              />

              <div className="mt-6 flex flex-wrap gap-4">
                <button
                  onClick={async () => {
                    setLoading(true);
                    setPostError(null);
                    setTokenResult(null);
                    const enforcementFields = buildEnforcementRequestFields(enforcementSimple);
                    const res = await fetch("/api/post-to-x", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ content: result, ...enforcementFields }),
                    });
                    const data = await res.json();
                    setLoading(false);
                    if (data.success) {
                      if (data.token_result) {
                        setTokenResult(data.token_result);
                        await refreshTokenLedger();
                      }
                      if (!data.token_result || data.token_result.mode === "off") {
                        await refreshTokenLedger();
                      }
                      setHistory((h) => [{ platform: 'X', content: result, time: new Date().toISOString() }, ...h].slice(0,5));
                      await refreshStreak();
                      alert(`Posted! ${data.url}`);
                    } else {
                      const message = data.error || data.message || "Post failed";
                      const suggestedFix =
                        data.suggestedFix ||
                        (data.code?.startsWith("ENFORCEMENT_")
                          ? "Regenerate content; receipt expired; click Generate again."
                          : undefined);
                      setPostError({ message, suggestedFix });
                      alert(`Error: ${message}`);
                    }
                  }}
                  disabled={loading}
                  className="px-10 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-xl text-2xl font-black"
                >
                  {loading ? "Posting..." : "Post to X Now"}
                </button>

                  <button
                    onClick={async () => {
                      setLoading(true);
                      const res = await fetch("/api/post-to-ig", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ content: result }),
                      });
                      const data = await res.json();
                      setLoading(false);
                      if (data.success) {
                        setHistory((h) => [{ platform: 'IG', content: result, time: new Date().toISOString() }, ...h].slice(0,5));
                        await refreshTokenLedger();
                        alert(`Posted to IG! id=${data.id}`);
                      } else {
                        alert(`IG error: ${JSON.stringify(data.error)}`);
                      }
                    }}
                    disabled={loading}
                    className="px-8 py-4 bg-gradient-to-r from-pink-500 to-yellow-400 rounded-xl text-xl font-bold"
                  >
                    {loading ? "Posting..." : "Post to IG Now"}
                  </button>
                  <button
                    onClick={async () => {
                      const minsInput = prompt("Schedule in how many minutes? (default 1)");
                      const mins = (minsInput ? Number(minsInput) : 1) || 1;
                      setLoading(true);
                      const res = await fetch("/api/schedule-post", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ content: result, delayMinutes: mins }),
                      });
                      const data = await res.json();
                      setLoading(false);
                      alert(data.scheduled ? `Scheduled in ${data.inMinutes}m` : `Schedule error: ${data.error}`);
                    }}
                    disabled={loading}
                    className="px-8 py-4 bg-gray-700 hover:bg-gray-600 rounded-xl text-xl font-bold"
                  >
                    Schedule for Later
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

        {/* ==== VIRAL THREAD GENERATOR ==== */}
        <div className="mt-8 bg-white/10 backdrop-blur-xl rounded-3xl p-10 shadow-2xl">
          <h2 className="text-4xl font-bold mb-8">🔥 Generate Full Viral Thread</h2>
          <p className="mb-4 text-gray-300">Multi-agent research → write → optimize pipeline</p>

          <textarea
            value={topicForThread}
            onChange={(e) => setTopicForThread(e.target.value)}
            placeholder="e.g., Why AI will replace content creators, Bootstrap SaaS revenue milestones, etc."
            className="w-full h-24 p-6 rounded-2xl bg-white/5 border border-white/20 text-white placeholder-white/50 text-xl focus:outline-none focus:border-purple-500 resize-none"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                generateViralThread();
              }
            }}
          />

          <button
            onClick={generateViralThread}
            disabled={loadingThread || !topicForThread.trim()}
            className="mt-8 px-12 py-6 bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-500 hover:to-pink-500 disabled:opacity-50 rounded-2xl text-2xl font-bold transition transform hover:scale-105"
          >
            {loadingThread ? "Researching & Writing..." : "Generate Full Thread"}
          </button>

          {threadLines.length > 0 && (
            <div className="mt-12 p-8 bg-black/40 rounded-2xl border border-pink-500">
              <strong>Generated Thread Preview:</strong>
              <div className="mt-4 space-y-3">
                {threadLines.map((line, idx) => (
                  <div key={idx} className="p-3 bg-white/5 rounded border border-white/10 text-sm leading-relaxed">
                    {line}
                  </div>
                ))}
              </div>
              <EnforcementBadge enforcement={enforcementThread} />
              <EnforcementErrorCallout
                message={threadPostError?.message}
                suggestedFix={threadPostError?.suggestedFix}
              />

              <div className="mt-6 flex flex-wrap gap-4">
                <button
                  onClick={async () => {
                    const threadContent = threadLines.join("\n");
                    setLoading(true);
                    setThreadPostError(null);
                    setTokenResult(null);
                    const enforcementFields = buildEnforcementRequestFields(enforcementThread);
                    const res = await fetch("/api/post-to-x", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ content: threadContent, ...enforcementFields }),
                    });
                    const data = await res.json();
                    setLoading(false);
                    if (data.success) {
                      if (data.token_result) {
                        setTokenResult(data.token_result);
                        await refreshTokenLedger();
                      }
                      if (!data.token_result || data.token_result.mode === "off") {
                        await refreshTokenLedger();
                      }
                      setThreadLines([]);
                      setTopicForThread("");
                      await refreshStreak();
                      alert(`Posted! ${data.url}`);
                    } else {
                      const message = data.error || data.message || "Post failed";
                      const suggestedFix =
                        data.suggestedFix ||
                        (data.code?.startsWith("ENFORCEMENT_")
                          ? "Regenerate content; receipt expired; click Generate again."
                          : undefined);
                      setThreadPostError({ message, suggestedFix });
                      alert(`Error: ${message}`);
                    }
                  }}
                  disabled={loading}
                  className="px-10 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-xl font-bold"
                >
                  {loading ? "Posting..." : "📤 Post Thread to X"}
                </button>

                <button
                  onClick={() => navigator.clipboard.writeText(threadLines.join("\n"))}
                  className="px-8 py-4 bg-gray-700 hover:bg-gray-600 rounded-xl font-bold"
                >
                  📋 Copy Thread
                </button>
              </div>
            </div>
          )}
        </div>

        <p className="text-center mt-20 text-xl opacity-70">
          Welcome back, {user?.firstName || "King"}
        </p>

        {/* ==== STREAK MOTIVATION ==== */}
        {streak && (
          <div className="mt-8 bg-gradient-to-r from-orange-600/20 to-red-600/20 backdrop-blur-xl rounded-3xl p-8 border border-orange-500/50 shadow-2xl">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-4xl font-black mb-2">You're on a {streak.current_length}-day streak 🔥</h3>
                <p className="text-lg text-white/80 mb-4">{streak.next_action_hint}</p>
                <div className="w-full max-w-md bg-white/10 rounded-full h-4 border border-orange-500/50 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-orange-500 to-red-500 h-full transition-all duration-300"
                    style={{ width: `${strideProgress * 100}%` }}
                  />
                </div>
                <p className="text-sm text-white/60 mt-2">{strideProgressRaw} / {protectionStride} days to protection window</p>
              </div>
              <div className="text-7xl">{streak.status === "grace" ? "🛡️" : streak.status === "decayed" ? "📉" : "🚀"}</div>
            </div>
          </div>
        )}

        {/* ==== TODAY'S CHALLENGE ==== */}
        {challenge && (
          <div className="mt-8 bg-gradient-to-r from-purple-600/20 to-blue-600/20 backdrop-blur-xl rounded-3xl p-8 border border-purple-500/50 shadow-2xl">
            <h3 className="text-3xl font-black mb-4">Today's Challenge 🎯</h3>
            <div className="mb-4">
              <span className="inline-block px-3 py-1 bg-purple-500/30 rounded-full text-sm font-bold mr-2">
                {challenge.type}
              </span>
              <span className="text-white/60 text-sm">{challenge.date}</span>
            </div>
            <p className="text-xl text-white/90 mb-6">{challenge.prompt}</p>
            <div className="flex items-center gap-4">
              {challenge.status === "assigned" && (
                <button
                  onClick={handleAcceptChallenge}
                  disabled={loadingChallenge}
                  className="px-8 py-3 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 rounded-xl font-bold"
                >
                  {loadingChallenge ? "..." : "Accept Challenge"}
                </button>
              )}
              {challenge.status === "accepted" && (
                <button
                  onClick={handleCompleteChallenge}
                  disabled={loadingChallenge}
                  className="px-8 py-3 bg-green-600 hover:bg-green-500 disabled:opacity-50 rounded-xl font-bold"
                >
                  {loadingChallenge ? "..." : "Mark Complete"}
                </button>
              )}
              {challenge.status === "completed" && (
                <div className="text-lg font-bold text-green-400">✓ Nice. You showed up today.</div>
              )}
              {challenge.status === "expired" && (
                <div className="text-lg text-white/60">A new challenge awaits tomorrow.</div>
              )}
            </div>
            <p className="text-sm text-white/60 mt-4">{challenge.next_action_hint}</p>
          </div>
        )}

        {/* RING Ledger */}
        <div className="mt-8 bg-white/5 p-6 rounded-2xl border border-white/10">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-2xl font-bold">RING Ledger</h3>
            {isAdmin && (
              <a href="/monitoring" className="text-sm text-yellow-300 hover:underline">Open monitoring</a>
            )}
          </div>
          <div className="flex flex-wrap gap-6 mb-4 text-lg">
            <div>
              <strong>Balance:</strong>{" "}
              <span className="text-yellow-300 font-bold">
                {tokenBalance !== null ? tokenBalance : "n/a"}
              </span>
            </div>
            <div>
              <strong>Pending:</strong>{" "}
              <span className="text-yellow-300 font-bold">{tokenPending}</span>
            </div>
            <div>
              <strong>Effective:</strong>{" "}
              <span className="text-yellow-300 font-bold">
                {tokenSummary?.effective_balance ?? tokenBalance ?? "n/a"}
              </span>
            </div>
            <div>
              <strong>Last Ledger:</strong>{" "}
              <span className="text-white/70 text-sm">
                {tokenSummary?.last_ledger_at ? new Date(tokenSummary.last_ledger_at).toLocaleString() : "n/a"}
              </span>
            </div>
            <div>
              <strong>Last Pending:</strong>{" "}
              <span className="text-white/70 text-sm">
                {tokenSummary?.last_pending_at ? new Date(tokenSummary.last_pending_at).toLocaleString() : "n/a"}
              </span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="border-b border-white/10">
                <tr>
                  <th className="py-2">Type</th>
                  <th className="py-2">Reason</th>
                  <th className="py-2">Amount</th>
                  <th className="py-2">Balance After</th>
                  <th className="py-2">Created</th>
                </tr>
              </thead>
              <tbody>
                {tokenLedger.map((entry) => (
                  <tr key={entry.id} className="border-b border-white/5">
                    <td className="py-2">{entry.eventType}</td>
                    <td className="py-2">{entry.reasonCode}</td>
                    <td className="py-2">{entry.amount}</td>
                    <td className="py-2">{entry.balanceAfter}</td>
                    <td className="py-2 text-xs text-gray-400">
                      {entry.createdAt ? new Date(entry.createdAt).toLocaleString() : "n/a"}
                    </td>
                  </tr>
                ))}
                {tokenLedger.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-4 opacity-60">
                      No ledger entries yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* RING Spending Actions */}
        <div className="mt-8 bg-white/5 p-6 rounded-2xl border border-white/10">
          <h3 className="text-2xl font-bold mb-4">RING Actions</h3>
          <div className="grid grid-cols-2 gap-4">
            <button
              onClick={async () => {
                try {
                  const res = await fetch("/api/ring/spend", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ action: "boost" }),
                  });
                  const data = await res.json();
                  if (!res.ok) return alert(data.error || "Failed to boost");
                  await refreshTokenLedger();
                  alert(data.message + " (-100 RING)");
                } catch (e) {
                  console.error(e);
                  alert("Boost failed");
                }
              }}
              className="px-6 py-3 bg-gradient-to-r from-red-500 to-orange-500 hover:from-red-600 hover:to-orange-600 rounded-lg font-bold text-lg"
            >
              🚀 Boost Latest Post (-100 RING)
            </button>
            <button
              onClick={async () => {
                try {
                  const res = await fetch("/api/ring/spend", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ action: "lease-username" }),
                  });
                  const data = await res.json();
                  if (!res.ok) return alert(data.error || "Failed to lease");
                  await refreshTokenLedger();
                  alert(data.message + " (-200 RING)");
                } catch (e) {
                  console.error(e);
                  alert("Lease failed");
                }
              }}
              className="px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 rounded-lg font-bold text-lg"
            >
              👑 Lease Premium Name (-200 RING)
            </button>
          </div>
        </div>

        {/* Referral & Promo */}
        <div className="mt-8 bg-white/5 p-6 rounded-2xl">
          <div className="flex gap-6 items-center">
            <div>
              <strong>Your Referral Code:</strong>
              <div className="mt-2">
                <button onClick={async () => {
                  try {
                    const res = await fetch('/api/referral/create');
                    const d = await res.json();
                    if (res.ok) setRefCode(d.code);
                    else alert(JSON.stringify(d));
                  } catch (e) { console.error(e); }
                }} className="px-3 py-2 bg-gray-800 rounded">Load Code</button>
                <span className="ml-3 font-mono">{refCode || '—'}</span>
              </div>
            </div>

            <div>
              <strong>Claim Referral</strong>
              <div className="mt-2 flex gap-2">
                <input value={claimInput} onChange={(e) => setClaimInput(e.target.value)} placeholder="CODE" className="px-3 py-2 rounded bg-white/5" />
                <button onClick={async () => {
                  try {
                    const res = await fetch('/api/referral/claim', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ code: claimInput }) });
                    const d = await res.json();
                    if (!res.ok) return alert(d.error || 'claim failed');
                    alert('Referral claimed! +200 RING each');
                    await refreshTokenLedger();
                  } catch (e) { console.error(e); alert('claim failed'); }
                }} className="px-3 py-2 bg-green-600 rounded">Claim</button>
              </div>
            </div>

            <div>
              <strong>Promo</strong>
              <div className="mt-2 flex gap-2">
                <input value={promoInput} onChange={(e) => setPromoInput(e.target.value)} placeholder="PROMO CODE" className="px-3 py-2 rounded bg-white/5" />
                <button onClick={async () => {
                  try {
                    const res = await fetch('/api/promo/claim', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ code: promoInput }) });
                    const d = await res.json();
                    if (!res.ok) return alert(d.error || 'promo failed');
                    alert(`Promo claimed! +${d.amount} RING`);
                    await refreshTokenLedger();
                  } catch (e) { console.error(e); alert('promo failed'); }
                }} className="px-3 py-2 bg-yellow-600 rounded">Claim Promo</button>
              </div>
            </div>
          </div>

          {/* Post history */}
          <div className="mt-12 mb-6 p-8 bg-white/5 rounded-2xl border border-white/10">
            <h3 className="text-3xl font-bold mb-6">Family Accounts</h3>
            <div className="text-lg mb-4">
              <strong>Combined RING Balance:</strong> <span className="text-yellow-300 font-bold">{combinedRingBalance}</span>
            </div>

            <div className="mb-6 flex gap-2">
              <input
                value={newMemberName}
                onChange={(e) => setNewMemberName(e.target.value)}
                placeholder="Member name (e.g. John, Jane)"
                className="flex-1 px-4 py-2 rounded bg-white/5 border border-white/10"
              />
              <button
                onClick={async () => {
                  if (!newMemberName.trim()) return alert("Please enter a name");
                  setLoadingFamily(true);
                  try {
                    const res = await fetch("/api/family/create", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ name: newMemberName }),
                    });
                    const data = await res.json();
                    if (!res.ok) return alert(data.error || "Failed to create family member");
                    setFamilyMembers([...familyMembers, data.familyMember]);
                    setCombinedRingBalance((c) => c + 0); // they start with 0
                    setNewMemberName("");
                    alert(`Created family member: ${newMemberName}`);
                  } catch (e) {
                    console.error(e);
                    alert("Failed to create family member");
                  } finally {
                    setLoadingFamily(false);
                  }
                }}
                disabled={loadingFamily}
                className="px-6 py-2 bg-purple-600 hover:bg-purple-500 rounded disabled:opacity-50"
              >
                {loadingFamily ? "Creating..." : "Create Member"}
              </button>
            </div>

            <div className="space-y-2">
              {familyMembers.length === 0 ? (
                <p className="opacity-60">No family members yet. Create one above.</p>
              ) : (
                familyMembers.map((member) => (
                  <div key={member.id} className="p-4 bg-white/5 rounded border border-white/10 flex items-center justify-between">
                    <div>
                      <strong>{member.name}</strong>
                      <span className="ml-3 text-yellow-300">RING: {member.ringBalance}</span>
                      {member.verified && (
                        <span className="ml-3 text-blue-400">
                          ✓ Verified
                        </span>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="mt-6">
            <strong>Recent Posts</strong>
            <table className="w-full mt-3 text-left">
              <thead><tr className="border-b border-white/10"><th>Platform</th><th>Content</th><th>Views</th><th>RING</th></tr></thead>
              <tbody>
                {history.map((p, idx) => (
                  <tr key={idx} className="border-b border-white/5"><td>{p.platform}</td><td className="truncate max-w-md">{p.content}</td><td>{(p as any).views ?? '—'}</td><td>{(p as any).ringEarned ?? '—'}</td></tr>
                ))}
                {history.length === 0 && <tr><td colSpan={4} className="py-4 opacity-60">No posts yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
