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

interface EnforcementRecord {
  request_id?: string | null;
  receipt_id?: string | null;
  mode?: string | null;
  qa_status?: string | null;
  audit_ok?: boolean;
  violation_codes_count?: number;
  created_at?: string | null;
  expires_at?: string | null;
  latency_ms?: number | null;
  last_error_code?: string | null;
  last_error_at?: string | null;
}

interface EnforcementMetrics {
  window_hours: number;
  metrics: {
    qa_blocked: number;
    enforcement_receipt_required: number;
    enforcement_receipt_expired: number;
    audit_write_failed: number;
    policy_error: number;
    p90_latency_ms?: number | null;
  };
}

interface TokenRecord {
  event_id: string;
  user_id: string;
  platform: string;
  published_at?: string | null;
  platform_post_id?: string | null;
  enforcement_request_id?: string | null;
  enforcement_receipt_id?: string | null;
  qa_status?: string | null;
  audit_ok?: boolean;
  token_mode?: string | null;
  token_issued_amount?: number | null;
  token_pending_amount?: number | null;
  token_reason_code?: string | null;
  token_ledger_id?: string | null;
  token_pending_id?: string | null;
  issuance_latency_ms?: number | null;
  created_at?: string | null;
  last_clerk_sync_at?: string | null;
  last_clerk_sync_error?: string | null;
}

interface TokenMetrics {
  window_hours: number;
  metrics: {
    total_issued: number;
    total_pending: number;
    blocked_issuance: number;
    top_reason_codes: Record<string, number>;
    p90_issuance_latency_ms?: number | null;
    reconciliation_mismatches?: number | null;
    clerk_sync_failures_24h?: number | null;
    idempotency_conflicts_24h?: number | null;
  };
}

export default function MonitoringPage() {
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const [stats, setStats] = useState<SystemStats | null>(null);
  const [traces, setTraces] = useState<AgentTrace[]>([]);
  const [enforcementRecords, setEnforcementRecords] = useState<EnforcementRecord[]>([]);
  const [enforcementMetrics, setEnforcementMetrics] = useState<EnforcementMetrics | null>(null);
  const [tokenRecords, setTokenRecords] = useState<TokenRecord[]>([]);
  const [tokenMetrics, setTokenMetrics] = useState<TokenMetrics | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [modeFilter, setModeFilter] = useState("all");
  const [auditOnly, setAuditOnly] = useState(false);
  const [searchRequestId, setSearchRequestId] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is admin (this is a stub - in production, check Clerk roles)
    if (isLoaded && user) {
      // For now, allow any authenticated user to view monitoring
      // In production: const isAdmin = user.publicMetadata?.role === 'admin'
      fetchStats();
      fetchEnforcement();
      fetchTokens();
      const interval = setInterval(() => {
        fetchStats();
        fetchEnforcement();
        fetchTokens();
      }, 10000); // Refresh every 10s
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

  const fetchEnforcement = async () => {
    try {
      const [recentRes, metricsRes] = await Promise.all([
        fetch("/api/monitoring/enforcement/recent?limit=100"),
        fetch("/api/monitoring/enforcement/metrics"),
      ]);
      const recentData = await recentRes.json();
      const metricsData = await metricsRes.json();
      if (recentRes.ok) {
        setEnforcementRecords(recentData.items || []);
      }
      if (metricsRes.ok) {
        setEnforcementMetrics(metricsData);
      }
    } catch (error) {
      console.error("[monitoring] enforcement fetch error:", error);
    }
  };

  const fetchTokens = async () => {
    try {
      const [recentRes, metricsRes] = await Promise.all([
        fetch("/api/monitoring/tokens/recent?limit=100"),
        fetch("/api/monitoring/tokens/metrics"),
      ]);
      const recentData = await recentRes.json();
      const metricsData = await metricsRes.json();
      if (recentRes.ok) {
        setTokenRecords(recentData.items || []);
      }
      if (metricsRes.ok) {
        setTokenMetrics(metricsData);
      }
    } catch (error) {
      console.error("[monitoring] token fetch error:", error);
    }
  };

  const filteredRecords = enforcementRecords.filter((record) => {
    if (statusFilter !== "all" && record.qa_status?.toLowerCase() !== statusFilter) {
      return false;
    }
    if (modeFilter !== "all" && record.mode?.toLowerCase() !== modeFilter) {
      return false;
    }
    if (auditOnly && record.audit_ok !== false) {
      return false;
    }
    if (searchRequestId && !record.request_id?.includes(searchRequestId)) {
      return false;
    }
    return true;
  });

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

        {/* Enforcement Monitoring */}
        <div className="mt-12 bg-white/10 backdrop-blur-xl rounded-3xl p-10 shadow-2xl border border-white/20">
          <h2 className="text-3xl font-bold mb-6">Enforcement Monitoring</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">QA_BLOCKED (24h)</div>
              <div className="text-2xl font-bold">{enforcementMetrics?.metrics.qa_blocked ?? 0}</div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">RECEIPT_REQUIRED (24h)</div>
              <div className="text-2xl font-bold">{enforcementMetrics?.metrics.enforcement_receipt_required ?? 0}</div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">RECEIPT_EXPIRED (24h)</div>
              <div className="text-2xl font-bold">{enforcementMetrics?.metrics.enforcement_receipt_expired ?? 0}</div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">AUDIT_WRITE_FAILED (24h)</div>
              <div className="text-2xl font-bold">{enforcementMetrics?.metrics.audit_write_failed ?? 0}</div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">POLICY_ERROR (24h)</div>
              <div className="text-2xl font-bold">{enforcementMetrics?.metrics.policy_error ?? 0}</div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">p90 Latency</div>
              <div className="text-2xl font-bold">
                {enforcementMetrics?.metrics.p90_latency_ms ?? "N/A"}
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-4 mb-6">
            <select
              data-testid="filter-status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm"
            >
              <option value="all">All status</option>
              <option value="pass">PASS</option>
              <option value="fail">FAIL</option>
            </select>
            <select
              data-testid="filter-mode"
              value={modeFilter}
              onChange={(e) => setModeFilter(e.target.value)}
              className="rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm"
            >
              <option value="all">All modes</option>
              <option value="advisory">ADVISORY</option>
              <option value="enforced">ENFORCED</option>
            </select>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={auditOnly}
                onChange={(e) => setAuditOnly(e.target.checked)}
              />
              Audit failures only
            </label>
            <input
              data-testid="search-request-id"
              value={searchRequestId}
              onChange={(e) => setSearchRequestId(e.target.value)}
              placeholder="Search request_id"
              className="rounded-lg bg-black/40 border border-white/10 px-3 py-2 text-sm flex-1 min-w-[220px]"
            />
          </div>

          {filteredRecords.length === 0 ? (
            <div className="text-gray-400 text-sm py-6">No enforcement records.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-gray-400">
                  <tr>
                    <th className="py-2">Timestamp</th>
                    <th className="py-2">Expires</th>
                    <th className="py-2">Mode</th>
                    <th className="py-2">QA</th>
                    <th className="py-2">Request</th>
                    <th className="py-2">Receipt</th>
                    <th className="py-2">Audit OK</th>
                    <th className="py-2">Violations</th>
                    <th className="py-2">Error</th>
                    <th className="py-2">Error At</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRecords.map((record, idx) => (
                    <tr key={`${record.request_id || "req"}-${idx}`} className="border-t border-white/10">
                      <td className="py-2 text-xs text-gray-300">
                        {record.created_at ? new Date(record.created_at).toLocaleString() : "n/a"}
                      </td>
                      <td className="py-2 text-xs text-gray-300">
                        {record.expires_at ? new Date(record.expires_at).toLocaleString() : "n/a"}
                      </td>
                      <td className="py-2">{record.mode?.toUpperCase() || "N/A"}</td>
                      <td className={`py-2 ${record.qa_status === "FAIL" ? "text-red-300" : "text-green-300"}`}>
                        {record.qa_status || "N/A"}
                      </td>
                      <td className="py-2 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{record.request_id || "n/a"}</span>
                          <button
                            type="button"
                            data-testid="copy-request-id"
                            onClick={() => navigator.clipboard.writeText(record.request_id || "")}
                            className="rounded bg-white/10 px-2 py-0.5 text-xs"
                          >
                            Copy
                          </button>
                        </div>
                      </td>
                      <td className="py-2 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{record.receipt_id || "n/a"}</span>
                          <button
                            type="button"
                            data-testid="copy-receipt-id"
                            onClick={() => navigator.clipboard.writeText(record.receipt_id || "")}
                            className="rounded bg-white/10 px-2 py-0.5 text-xs"
                          >
                            Copy
                          </button>
                        </div>
                      </td>
                      <td className="py-2">{record.audit_ok ? "YES" : "NO"}</td>
                      <td className="py-2">{record.violation_codes_count ?? 0}</td>
                      <td className="py-2 text-xs text-red-200">
                        {record.last_error_code || "n/a"}
                      </td>
                      <td className="py-2 text-xs text-red-200">
                        {record.last_error_at ? new Date(record.last_error_at).toLocaleString() : "n/a"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Token Monitoring */}
        <div className="mt-12 bg-white/10 backdrop-blur-xl rounded-3xl p-10 shadow-2xl border border-white/20">
          <h2 className="text-3xl font-bold mb-6">Token Monitoring</h2>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">Total Issued (24h)</div>
              <div className="text-2xl font-bold">{tokenMetrics?.metrics.total_issued ?? 0}</div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">Total Pending (24h)</div>
              <div className="text-2xl font-bold">{tokenMetrics?.metrics.total_pending ?? 0}</div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">Blocked Issuance (24h)</div>
              <div className="text-2xl font-bold">{tokenMetrics?.metrics.blocked_issuance ?? 0}</div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">p90 Issuance Latency</div>
              <div className="text-2xl font-bold">
                {tokenMetrics?.metrics.p90_issuance_latency_ms ?? "N/A"}
              </div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">Reconciliation Mismatches (24h)</div>
              <div className="text-2xl font-bold">{tokenMetrics?.metrics.reconciliation_mismatches ?? 0}</div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">Clerk Sync Failures (24h)</div>
              <div className="text-2xl font-bold">{tokenMetrics?.metrics.clerk_sync_failures_24h ?? 0}</div>
            </div>
            <div className="bg-black/40 rounded-xl p-4 border border-white/10">
              <div className="text-sm text-gray-400">Idempotency Conflicts (24h)</div>
              <div className="text-2xl font-bold">{tokenMetrics?.metrics.idempotency_conflicts_24h ?? 0}</div>
            </div>
          </div>

          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-2">Top Reason Codes (24h)</h3>
            {tokenMetrics?.metrics.top_reason_codes && Object.keys(tokenMetrics.metrics.top_reason_codes).length ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {Object.entries(tokenMetrics.metrics.top_reason_codes).map(([code, count]) => (
                  <div key={code} className="bg-black/40 rounded-lg p-3 border border-white/10 text-sm">
                    <div className="text-gray-400">{code}</div>
                    <div className="text-xl font-bold">{count}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-gray-400 text-sm">No reason code data yet.</div>
            )}
          </div>

          {tokenRecords.length === 0 ? (
            <div className="text-gray-400 text-sm py-6">No token publish events.</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-gray-400">
                  <tr>
                    <th className="py-2">Created</th>
                    <th className="py-2">Platform</th>
                    <th className="py-2">Event</th>
                    <th className="py-2">Request</th>
                    <th className="py-2">Receipt</th>
                    <th className="py-2">Ledger</th>
                    <th className="py-2">Pending</th>
                    <th className="py-2">Issued</th>
                    <th className="py-2">Reason</th>
                    <th className="py-2">Clerk Sync</th>
                    <th className="py-2">Clerk Error</th>
                  </tr>
                </thead>
                <tbody>
                  {tokenRecords.map((record, idx) => (
                    <tr key={`${record.event_id}-${idx}`} className="border-t border-white/10">
                      <td className="py-2 text-xs text-gray-300">
                        {record.created_at ? new Date(record.created_at).toLocaleString() : "n/a"}
                      </td>
                      <td className="py-2">{record.platform?.toUpperCase() || "N/A"}</td>
                      <td className="py-2 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{record.event_id}</span>
                          <button
                            type="button"
                            data-testid="copy-event-id"
                            onClick={() => navigator.clipboard.writeText(record.event_id || "")}
                            className="rounded bg-white/10 px-2 py-0.5 text-xs"
                          >
                            Copy
                          </button>
                        </div>
                      </td>
                      <td className="py-2 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{record.enforcement_request_id || "n/a"}</span>
                          <button
                            type="button"
                            data-testid="copy-token-request-id"
                            onClick={() => navigator.clipboard.writeText(record.enforcement_request_id || "")}
                            className="rounded bg-white/10 px-2 py-0.5 text-xs"
                          >
                            Copy
                          </button>
                        </div>
                      </td>
                      <td className="py-2 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{record.enforcement_receipt_id || "n/a"}</span>
                          <button
                            type="button"
                            data-testid="copy-token-receipt-id"
                            onClick={() => navigator.clipboard.writeText(record.enforcement_receipt_id || "")}
                            className="rounded bg-white/10 px-2 py-0.5 text-xs"
                          >
                            Copy
                          </button>
                        </div>
                      </td>
                      <td className="py-2 text-xs">
                        <div className="flex items-center gap-2">
                          <span className="font-mono">{record.token_ledger_id || "n/a"}</span>
                          <button
                            type="button"
                            data-testid="copy-token-ledger-id"
                            onClick={() => navigator.clipboard.writeText(record.token_ledger_id || "")}
                            className="rounded bg-white/10 px-2 py-0.5 text-xs"
                          >
                            Copy
                          </button>
                        </div>
                      </td>
                      <td className="py-2 text-xs">{record.token_pending_id || "n/a"}</td>
                      <td className="py-2">{record.token_issued_amount ?? 0}</td>
                      <td className="py-2">{record.token_reason_code || "n/a"}</td>
                      <td className="py-2 text-xs text-gray-300">
                        {record.last_clerk_sync_at ? new Date(record.last_clerk_sync_at).toLocaleString() : "n/a"}
                      </td>
                      <td className="py-2 text-xs text-red-200">
                        {record.last_clerk_sync_error || "n/a"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-12 text-center text-gray-500 text-sm">
          <p>Dashboard auto-refreshes every 10 seconds</p>
          <p>Last updated: {new Date().toLocaleTimeString()}</p>
        </div>
      </div>
    </div>
  );
}
