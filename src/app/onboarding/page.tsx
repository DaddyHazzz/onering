"use client";

import { useState } from "react";
import { useUser, SignInButton, UserButton } from "@clerk/nextjs";
import { loadStripe } from "@stripe/stripe-js";
import { useRouter } from "next/navigation";

const stripePromise = loadStripe(
  process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!
);

export default function OnboardingPage() {
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const [step, setStep] = useState<
    "signin" | "connect-x" | "verification" | "family" | "complete"
  >("signin");
  const [loading, setLoading] = useState(false);
  const [familyName, setFamilyName] = useState("");
  const [xConnected, setXConnected] = useState(false);
  const [igConnected, setIgConnected] = useState(false);

  if (!isLoaded) {
    return <div className="min-h-screen bg-purple-900 text-white flex items-center justify-center">Loading...</div>;
  }

  // If user not signed in, show sign-in step
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 text-white flex items-center justify-center p-10">
        <div className="max-w-xl w-full bg-white/10 backdrop-blur-xl rounded-3xl p-12 shadow-2xl text-center">
          <h1 className="text-6xl font-black mb-6">OneRing</h1>
          <p className="text-2xl mb-12 text-gray-300">
            The AI-powered social growth engine. Start your journey.
          </p>
          <SignInButton mode="modal" forceRedirectUrl="/onboarding">
            <button className="px-12 py-6 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 rounded-2xl text-2xl font-bold w-full">
              Sign In with Clerk
            </button>
          </SignInButton>
        </div>
      </div>
    );
  }

  // Redirect to dashboard if onboarding is complete
  if (step === "complete") {
    setTimeout(() => router.push("/dashboard"), 2000);
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-blue-900 text-white p-10">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center justify-between mb-12">
          <h1 className="text-6xl font-black">OneRing</h1>
          <UserButton afterSignOutUrl="/" />
        </div>

        {/* Step 1: Connect X */}
        {step === "signin" && (
          <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-10 shadow-2xl">
            <h2 className="text-4xl font-bold mb-8">Step 1: Connect Your X Account</h2>
            <p className="text-xl mb-8 text-gray-300">
              Link your X (Twitter) account to start posting viral content.
            </p>

            <div className="space-y-6">
              <div className="p-6 bg-black/40 rounded-xl border border-blue-500">
                <p className="text-lg mb-4">X Account Status:</p>
                {xConnected ? (
                  <div className="text-green-400 font-bold text-xl">✓ Connected</div>
                ) : (
                  <button
                    onClick={() => {
                      console.log("[onboarding] X auth flow (stub)");
                      setXConnected(true);
                    }}
                    className="px-8 py-4 bg-blue-600 hover:bg-blue-500 rounded-lg text-xl font-bold w-full"
                  >
                    Connect X Account
                  </button>
                )}
              </div>

              <div className="p-6 bg-black/40 rounded-xl border border-pink-500">
                <p className="text-lg mb-4">Instagram Account Status:</p>
                {igConnected ? (
                  <div className="text-green-400 font-bold text-xl">✓ Connected</div>
                ) : (
                  <button
                    onClick={() => {
                      console.log("[onboarding] IG auth flow (stub)");
                      setIgConnected(true);
                    }}
                    className="px-8 py-4 bg-pink-600 hover:bg-pink-500 rounded-lg text-xl font-bold w-full"
                  >
                    Connect Instagram Account
                  </button>
                )}
              </div>
            </div>

            <button
              onClick={() => setStep("verification")}
              disabled={!xConnected}
              className="mt-12 px-12 py-6 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 disabled:opacity-50 rounded-2xl text-2xl font-bold w-full"
            >
              Next: Get Verified →
            </button>
          </div>
        )}

        {/* Step 2: Verification */}
        {step === "verification" && (
          <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-10 shadow-2xl">
            <h2 className="text-4xl font-bold mb-8">Step 2: Get Verified Blue Check</h2>
            <p className="text-xl mb-8 text-gray-300">
              Unlock premium features with official verification ($99/year).
            </p>

            <div className="p-8 bg-gradient-to-r from-yellow-400/20 to-yellow-600/20 rounded-2xl border border-yellow-500 mb-8">
              <div className="flex items-center gap-4 mb-4">
                <svg
                  className="w-12 h-12 text-yellow-400"
                  fill="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path d="M22.5 12.5l-9.99 10-6.01-6 1.42-1.42L12.5 19.66l8.58-8.58z" />
                </svg>
                <span className="text-3xl font-bold">Verified Badge</span>
              </div>
              <p className="text-lg text-gray-300">+500 RING bonus + Premium analytics</p>
            </div>

            <button
              onClick={async () => {
                setLoading(true);
                try {
                  const res = await fetch("/api/stripe/checkout");
                  const data = await res.json();
                  if (data.sessionUrl) {
                    window.location.href = data.sessionUrl;
                  } else {
                    alert("Failed to create checkout session");
                  }
                } catch (e) {
                  alert("Error: " + String(e));
                } finally {
                  setLoading(false);
                }
              }}
              disabled={loading}
              className="px-12 py-6 bg-gradient-to-r from-yellow-400 to-yellow-600 hover:from-yellow-500 hover:to-yellow-700 disabled:opacity-50 rounded-2xl text-2xl font-bold w-full mb-6 text-black"
            >
              {loading ? "Redirecting..." : "Pay $99 for Verification"}
            </button>

            <button
              onClick={() => setStep("family")}
              className="px-12 py-4 bg-gray-700 hover:bg-gray-600 rounded-2xl text-xl font-bold w-full"
            >
              Skip for Now
            </button>
          </div>
        )}

        {/* Step 3: Family Members */}
        {step === "family" && (
          <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-10 shadow-2xl">
            <h2 className="text-4xl font-bold mb-8">Step 3: Create Family Members</h2>
            <p className="text-xl mb-8 text-gray-300">
              Add team members or alternate accounts to your family pool (optional).
            </p>

            <div className="space-y-6 mb-8">
              <div>
                <label className="block text-lg font-semibold mb-3">Family Member Name</label>
                <input
                  type="text"
                  value={familyName}
                  onChange={(e) => setFamilyName(e.target.value)}
                  placeholder="e.g. @my_alt_account"
                  className="w-full px-6 py-4 rounded-xl bg-black/40 border border-white/20 text-white placeholder-white/50 text-lg focus:border-purple-500 outline-none"
                />
              </div>

              <button
                onClick={async () => {
                  if (!familyName.trim()) {
                    alert("Enter a family member name");
                    return;
                  }
                  setLoading(true);
                  try {
                    const res = await fetch("/api/family/add", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ name: familyName }),
                    });
                    const data = await res.json();
                    if (res.ok) {
                      alert(`Added ${familyName}`);
                      setFamilyName("");
                    } else {
                      alert(data.error || "Failed to add family member");
                    }
                  } catch (e) {
                    alert("Error: " + String(e));
                  } finally {
                    setLoading(false);
                  }
                }}
                disabled={loading || !familyName.trim()}
                className="px-8 py-4 bg-purple-600 hover:bg-purple-500 disabled:opacity-50 rounded-xl text-xl font-bold w-full"
              >
                Add Family Member
              </button>
            </div>

            <button
              onClick={() => setStep("complete")}
              className="px-12 py-6 bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-500 hover:to-blue-500 rounded-2xl text-2xl font-bold w-full"
            >
              Complete Onboarding →
            </button>
          </div>
        )}

        {/* Completion */}
        {step === "complete" && (
          <div className="bg-white/10 backdrop-blur-xl rounded-3xl p-10 shadow-2xl text-center">
            <div className="text-8xl mb-6">🎉</div>
            <h2 className="text-4xl font-bold mb-6">Welcome to OneRing!</h2>
            <p className="text-2xl text-gray-300 mb-8">
              Onboarding complete. Redirecting to dashboard...
            </p>
          </div>
        )}

        {/* Step Indicators */}
        <div className="mt-12 flex justify-between text-sm">
          {["signin", "verification", "family", "complete"].map((s) => (
            <div
              key={s}
              className={`px-4 py-2 rounded-lg font-semibold ${
                step === s
                  ? "bg-purple-600 text-white"
                  : step === "complete" || (
                      ["signin", "verification", "family", "complete"].indexOf(step) >
                      ["signin", "verification", "family", "complete"].indexOf(s)
                    )
                  ? "bg-green-600 text-white"
                  : "bg-gray-700 text-gray-300"
              }`}
            >
              {s === "signin" && "1. Connect"}
              {s === "verification" && "2. Verify"}
              {s === "family" && "3. Family"}
              {s === "complete" && "✓ Done"}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
