"use client";

import { useState } from "react";

export default function AdminBillingPage() {
  const [adminKey, setAdminKey] = useState("");
  const [retries, setRetries] = useState<any[]>([]);
  const [subs, setSubs] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const baseUrl = typeof window !== "undefined" ? "http://localhost:8000" : "";

  const fetchRetries = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${baseUrl}/v1/admin/billing/retries`, {
        headers: { "X-Admin-Key": adminKey },
      });
      const json = await res.json();
      if (res.ok) setRetries(json);
      else alert(json?.detail || "Failed to fetch retries");
    } finally {
      setLoading(false);
    }
  };

  const fetchSubscriptions = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${baseUrl}/v1/admin/billing/subscriptions`, {
        headers: { "X-Admin-Key": adminKey },
      });
      const json = await res.json();
      if (res.ok) setSubs(json);
      else alert(json?.detail || "Failed to fetch subscriptions");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-semibold">Admin Billing</h1>
      <div className="space-y-2">
        <label className="block text-sm">Admin Key (X-Admin-Key)</label>
        <input
          value={adminKey}
          onChange={(e) => setAdminKey(e.target.value)}
          placeholder="Enter admin key"
          className="border rounded px-3 py-2 w-full"
        />
      </div>
      <div className="flex gap-3">
        <button onClick={fetchRetries} className="px-4 py-2 bg-blue-600 text-white rounded" disabled={loading}>
          List Retries
        </button>
        <button onClick={fetchSubscriptions} className="px-4 py-2 bg-gray-700 text-white rounded" disabled={loading}>
          List Subscriptions
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-lg font-medium">Retries</h2>
          <pre className="bg-gray-100 p-3 rounded overflow-auto max-h-96">{JSON.stringify(retries, null, 2)}</pre>
        </div>
        <div>
          <h2 className="text-lg font-medium">Subscriptions</h2>
          <pre className="bg-gray-100 p-3 rounded overflow-auto max-h-96">{JSON.stringify(subs, null, 2)}</pre>
        </div>
      </div>
    </div>
  );
}
