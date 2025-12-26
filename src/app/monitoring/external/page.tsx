"use client";

import { useState, useEffect } from "react";
import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

interface WebhookMetrics {
  delivered: number;
  failed: number;
  dead: number;
  pending: number;
  delivering: number;
  retrying: number;
}

interface ExternalKeyMetrics {
  tier: string;
  active: number;
  revoked: number;
}

interface ExternalKeySummary {
  totals: ExternalKeyMetrics[];
  total_active: number;
  total_revoked: number;
  last_used_at: string | null;
}

interface WebhookDeliveryItem {
  id: string;
  webhook_id: string;
  event_id: string;
  event_type: string;
  status: string;
  attempts: number;
  last_status_code: number | null;
  last_error: string | null;
  created_at: string;
  next_attempt_at: string | null;
}

export default function ExternalMonitoringPage() {
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const [adminKey, setAdminKey] = useState("");
  const [webhookMetrics, setWebhookMetrics] = useState<WebhookMetrics | null>(null);
  const [keyMetrics, setKeyMetrics] = useState<ExternalKeySummary | null>(null);
  const [recentDeliveries, setRecentDeliveries] = useState<WebhookDeliveryItem[]>([]);
  const [filterStatus, setFilterStatus] = useState<string>("");
  const [filterEventType, setFilterEventType] = useState<string>("");
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (isLoaded && !user) {
      router.push("/");
    }
  }, [isLoaded, user, router]);

  const headers = {
    "Content-Type": "application/json",
    "X-Admin-Key": adminKey,
  };

  const fetchData = async () => {
    if (!adminKey) return;
    setError("");
    try {
      const [webhooksRes, keysRes, deliveriesRes] = await Promise.all([
        fetch("/api/monitoring/webhooks/metrics", { headers }),
        fetch("/api/monitoring/external/keys", { headers }),
        fetch(
          `/api/monitoring/webhooks/recent?status=${filterStatus}&event_type=${filterEventType}&limit=30`,
          { headers }
        ),
      ]);

      if (webhooksRes.ok) {
        const data = await webhooksRes.json();
        setWebhookMetrics(data);
      } else {
        setError("Failed to fetch webhook metrics. Check admin key.");
      }
      if (keysRes.ok) {
        const data = await keysRes.json();
        setKeyMetrics(data);
      }
      if (deliveriesRes.ok) {
        const data = await deliveriesRes.json();
        setRecentDeliveries(data.deliveries || []);
      }
      setLastRefresh(new Date());
    } catch (err: any) {
      setError(err.message || "Failed to fetch data");
    }
  };

  useEffect(() => {
    if (!adminKey || !autoRefresh) return;
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [adminKey, autoRefresh, filterStatus, filterEventType]);

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-50 flex items-center justify-center">
        <div className="text-xl">Loading...</div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        <header className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-black">External Platform Monitoring</h1>
            <p className="text-slate-400 mt-1">Real-time metrics for API keys and webhooks</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              Auto-refresh (5s)
            </label>
            <button
              onClick={fetchData}
              className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-lg px-4 py-2"
            >
              Refresh Now
            </button>
          </div>
        </header>

        {lastRefresh && (
          <div className="text-xs text-slate-500">Last updated: {lastRefresh.toLocaleTimeString()}</div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-300 text-sm">
            {error}
          </div>
        )}

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
          <label className="block text-sm text-slate-300">Admin Key (X-Admin-Key)</label>
          <input
            type="password"
            className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
            placeholder="Enter admin key to view metrics"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
          />
          <p className="text-xs text-slate-500">Required for all monitoring data. Set ONERING_ADMIN_KEY in backend env.</p>
        </div>

        {/* External API Keys Section */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-2xl font-bold">External API Keys</h2>
          {keyMetrics ? (
            <div className="space-y-4">
              <div className="grid md:grid-cols-3 gap-4">
                <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4">
                  <div className="text-emerald-300 text-3xl font-black">{keyMetrics.total_active}</div>
                  <div className="text-slate-400 text-sm">Active Keys</div>
                </div>
                <div className="bg-slate-700/30 border border-slate-700 rounded-lg p-4">
                  <div className="text-slate-300 text-3xl font-black">{keyMetrics.total_revoked}</div>
                  <div className="text-slate-400 text-sm">Revoked Keys</div>
                </div>
                <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                  <div className="text-blue-300 text-sm font-semibold">Last Used</div>
                  <div className="text-slate-300 text-xs mt-1">
                    {keyMetrics.last_used_at
                      ? new Date(keyMetrics.last_used_at).toLocaleString()
                      : "Never"}
                  </div>
                </div>
              </div>
              <div className="space-y-2">
                <h3 className="text-lg font-semibold text-slate-300">By Tier</h3>
                <div className="grid md:grid-cols-3 gap-3">
                  {keyMetrics.totals.map((tm) => (
                    <div
                      key={tm.tier}
                      className="border border-slate-800 rounded-lg p-3 bg-slate-950/40"
                    >
                      <div className="text-sm font-semibold text-slate-200 uppercase">{tm.tier}</div>
                      <div className="text-xs text-slate-400">
                        Active: {tm.active} / Revoked: {tm.revoked}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-slate-500 text-sm">No data. Enter admin key and refresh.</div>
          )}
        </section>

        {/* Webhooks Section */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-2xl font-bold">Webhooks Delivery</h2>
          {webhookMetrics ? (
            <div className="grid md:grid-cols-6 gap-3">
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4">
                <div className="text-emerald-300 text-2xl font-black">{webhookMetrics.delivered}</div>
                <div className="text-slate-400 text-xs">Delivered</div>
              </div>
              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                <div className="text-yellow-300 text-2xl font-black">{webhookMetrics.pending}</div>
                <div className="text-slate-400 text-xs">Pending</div>
              </div>
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
                <div className="text-blue-300 text-2xl font-black">{webhookMetrics.delivering}</div>
                <div className="text-slate-400 text-xs">Delivering</div>
              </div>
              <div className="bg-orange-500/10 border border-orange-500/30 rounded-lg p-4">
                <div className="text-orange-300 text-2xl font-black">{webhookMetrics.retrying}</div>
                <div className="text-slate-400 text-xs">Retrying</div>
              </div>
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
                <div className="text-red-300 text-2xl font-black">{webhookMetrics.failed}</div>
                <div className="text-slate-400 text-xs">Failed</div>
              </div>
              <div className="bg-slate-700/30 border border-slate-700 rounded-lg p-4">
                <div className="text-slate-300 text-2xl font-black">{webhookMetrics.dead}</div>
                <div className="text-slate-400 text-xs">Dead</div>
              </div>
            </div>
          ) : (
            <div className="text-slate-500 text-sm">No data. Enter admin key and refresh.</div>
          )}
        </section>

        {/* Recent Deliveries */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold">Recent Deliveries</h2>
            <div className="flex gap-3">
              <select
                className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-1 text-sm"
                value={filterStatus}
                onChange={(e) => setFilterStatus(e.target.value)}
              >
                <option value="">All Status</option>
                <option value="succeeded">Succeeded</option>
                <option value="pending">Pending</option>
                <option value="failed">Failed</option>
                <option value="dead">Dead</option>
                <option value="delivering">Delivering</option>
              </select>
              <select
                className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-1 text-sm"
                value={filterEventType}
                onChange={(e) => setFilterEventType(e.target.value)}
              >
                <option value="">All Events</option>
                <option value="draft.published">draft.published</option>
                <option value="ring.earned">ring.earned</option>
                <option value="enforcement.failed">enforcement.failed</option>
              </select>
            </div>
          </div>
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {recentDeliveries.length > 0 ? (
              recentDeliveries.map((d) => (
                <div
                  key={d.id}
                  className="border border-slate-800 rounded-lg p-3 bg-slate-950/40 space-y-2 text-sm"
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <span className="font-mono text-slate-300">{d.event_type}</span>
                      <span className="text-slate-500 ml-2 text-xs">({d.event_id.slice(0, 12)}...)</span>
                    </div>
                    <StatusBadge status={d.status} />
                  </div>
                  <div className="text-xs text-slate-400 space-y-1">
                    <div>Attempts: {d.attempts}</div>
                    {d.last_status_code && <div>HTTP: {d.last_status_code}</div>}
                    {d.last_error && (
                      <div className="text-red-400 max-w-full break-words">Error: {d.last_error}</div>
                    )}
                    <div>Created: {new Date(d.created_at).toLocaleString()}</div>
                    {d.next_attempt_at && (
                      <div>Next Retry: {new Date(d.next_attempt_at).toLocaleString()}</div>
                    )}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-slate-500 text-sm">No deliveries found.</div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    succeeded: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
    pending: "bg-yellow-500/20 text-yellow-300 border-yellow-500/40",
    delivering: "bg-blue-500/20 text-blue-300 border-blue-500/40",
    failed: "bg-red-500/20 text-red-300 border-red-500/40",
    dead: "bg-slate-700/50 text-slate-400 border-slate-600",
  };
  const style = styles[status] || styles.pending;
  return (
    <span className={`text-xs font-semibold px-2 py-1 rounded border ${style}`}>
      {status.toUpperCase()}
    </span>
  );
}
