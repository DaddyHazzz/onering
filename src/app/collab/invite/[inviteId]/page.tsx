/**
 * src/app/collab/invite/[inviteId]/page.tsx
 * Deep link: Accept collaboration invite with token
 */

"use client";

import { useUser } from "@clerk/nextjs";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { useState, useEffect } from "react";

export default function AcceptInvitePage() {
  const { user, isLoaded } = useUser();
  const params = useParams();
  const searchParams = useSearchParams();
  const router = useRouter();

  const inviteId = params.inviteId as string;
  const token = searchParams.get("token");

  const [manualToken, setManualToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [draftId, setDraftId] = useState<string | null>(null);

  useEffect(() => {
    // Auto-accept if signed in and token present
    if (isLoaded && user && token) {
      handleAccept(token);
    }
  }, [isLoaded, user, token]);

  const handleAccept = async (tokenToUse: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/collab/invites/${inviteId}/accept`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          token: tokenToUse,
        }),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to accept invite");
      }

      const data = await res.json();
      setSuccess(true);
      setDraftId(data.data.draft_id);
      
      // Auto-redirect after brief success display
      setTimeout(() => {
        router.push(`/dashboard/collab?draftId=${data.data.draft_id}&joined=1`);
      }, 1500);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleManualAccept = (e: React.FormEvent) => {
    e.preventDefault();
    if (manualToken.trim()) {
      handleAccept(manualToken.trim());
    }
  };

  const goToDraft = () => {
    if (draftId) {
      router.push(`/dashboard/collab?draftId=${draftId}&joined=1`);
    }
  };

  // Not loaded yet
  if (!isLoaded) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  // Not signed in
  if (!user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md p-8 bg-white rounded-lg shadow text-center">
          <h1 className="text-2xl font-bold mb-4">Welcome to the Collaboration</h1>
          <p className="text-gray-700 mb-6">
            Sign in to accept this invite and start creating together.
          </p>
          <a
            href="/sign-in"
            className="inline-block px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Sign In
          </a>
        </div>
      </div>
    );
  }

  // Success state
  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md p-8 bg-white rounded-lg shadow text-center">
          <div className="text-green-600 text-5xl mb-4">✅</div>
          <h1 className="text-2xl font-bold mb-4">You're in!</h1>
          <p className="text-gray-700 mb-6">
            Welcome to the collaboration. Ready to create together?
          </p>
          <button
            onClick={goToDraft}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Open the Draft
          </button>
        </div>
      </div>
    );
  }

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md p-8 bg-white rounded-lg shadow text-center">
          <p className="text-gray-700">Accepting invite...</p>
        </div>
      </div>
    );
  }

  // Error or no token (show manual input)
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md p-8 bg-white rounded-lg shadow">
        <h1 className="text-2xl font-bold mb-4">Accept Invite</h1>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded">
            <p className="text-sm text-red-800">{error}</p>
            <p className="text-xs text-gray-600 mt-2">
              {error.includes("expired") &&
                "This invite has expired. Ask the draft owner for a new one."}
              {error.includes("revoked") &&
                "This invite was revoked. Contact the draft owner."}
              {error.includes("invalid") &&
                "Check your token and try again, or request a new invite."}
            </p>
          </div>
        )}

        {!token && (
          <div className="mb-6">
            <p className="text-sm text-gray-700 mb-4">
              No token found in the URL. Paste your invite token below:
            </p>
            <form onSubmit={handleManualAccept} className="space-y-3">
              <input
                type="text"
                value={manualToken}
                onChange={(e) => setManualToken(e.target.value)}
                placeholder="Paste invite token here"
                required
                className="w-full px-3 py-2 border rounded"
              />
              <button
                type="submit"
                disabled={loading}
                className="w-full px-4 py-2 bg-purple-600 text-white rounded hover:bg-purple-700 disabled:opacity-50"
              >
                {loading ? "Accepting..." : "Accept Invite"}
              </button>
            </form>
          </div>
        )}

        <div className="text-center">
          <a href="/dashboard/collab" className="text-sm text-blue-600 hover:underline">
            Go to Collaborations
          </a>
        </div>
      </div>
    </div>
  );
}
