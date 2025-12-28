"use client";

import { useState } from "react";
import { OrgBadge } from "@/components/OrgBadge";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
const scopes = ["read:rings", "read:drafts", "read:ledger", "read:enforcement"];
const webhookEvents = ["draft.published", "ring.earned", "enforcement.failed"];
const tiers = ["free", "pro", "enterprise"];

export default function AdminExternalPage() {
  const [adminKey, setAdminKey] = useState("");
  const [filterOrgId, setFilterOrgId] = useState<string>(""); // Admin can filter by org
  const [ownerUserId, setOwnerUserId] = useState("");
  const [selectedScopes, setSelectedScopes] = useState<string[]>(["read:rings"]);
  const [tier, setTier] = useState("free");
  const [expiresInDays, setExpiresInDays] = useState<string>("");
  const [ipAllowlist, setIpAllowlist] = useState<string>("");
  const [canaryEnabled, setCanaryEnabled] = useState(false);
  const [createResult, setCreateResult] = useState<any>(null);
  const [rotateResult, setRotateResult] = useState<any>(null);
  const [listKeys, setListKeys] = useState<any[]>([]);
  const [keyId, setKeyId] = useState("");
  const [rotatePreserve, setRotatePreserve] = useState(true);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookOwner, setWebhookOwner] = useState("");
  const [webhookEventsSelected, setWebhookEventsSelected] = useState<string[]>([webhookEvents[0]]);
  const [webhookResult, setWebhookResult] = useState<any>(null);
  const [deleteWebhookId, setDeleteWebhookId] = useState("");
  const [deleteWebhookOwner, setDeleteWebhookOwner] = useState("");
  const [statusMessage, setStatusMessage] = useState<string>("");

  const headers = {
    "Content-Type": "application/json",
    "X-Admin-Key": adminKey,
    ...(filterOrgId && { "X-Org-ID": filterOrgId }),
  } as Record<string, string>;

  const handleScopeToggle = (value: string) => {
    setSelectedScopes((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]
    );
  };

  const handleEventToggle = (value: string) => {
    setWebhookEventsSelected((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value]
    );
  };

  const parseAllowlist = () =>
    ipAllowlist
      .split(/[,\n]/)
      .map((ip) => ip.trim())
      .filter(Boolean);

  const createKey = async () => {
    setStatusMessage("Creating key...");
    const res = await fetch(`${BACKEND_URL}/v1/admin/external/keys`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        owner_user_id: ownerUserId,
        scopes: selectedScopes,
        tier,
        canary_enabled: canaryEnabled,
        expires_in_days: expiresInDays ? Number(expiresInDays) : undefined,
        ip_allowlist: parseAllowlist(),
      }),
    });
    const data = await res.json();
    setStatusMessage(res.ok ? "Key created" : data.detail || "Failed to create key");
    setCreateResult(data);
  };

  const rotateKey = async () => {
    setStatusMessage("Rotating key...");
    const res = await fetch(`${BACKEND_URL}/v1/admin/external/keys/${keyId}/rotate`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        preserve_key_id: rotatePreserve,
        expires_in_days: expiresInDays ? Number(expiresInDays) : undefined,
        ip_allowlist: parseAllowlist(),
      }),
    });
    const data = await res.json();
    setStatusMessage(res.ok ? "Key rotated" : data.detail || "Rotate failed");
    setRotateResult(data);
  };

  const revokeKey = async () => {
    setStatusMessage("Revoking key...");
    const res = await fetch(`${BACKEND_URL}/v1/admin/external/keys/${keyId}/revoke`, {
      method: "POST",
      headers,
    });
    const data = await res.json();
    setStatusMessage(res.ok ? "Key revoked" : data.detail || "Revoke failed");
  };

  const fetchKeys = async () => {
    const res = await fetch(`${BACKEND_URL}/v1/admin/external/keys/${ownerUserId}`, {
      headers,
    });
    const data = await res.json();
    if (res.ok) {
      setListKeys(data.keys || []);
      setStatusMessage("Keys loaded");
    } else {
      setStatusMessage(data.detail || "Failed to load keys");
    }
  };

  const createWebhook = async () => {
    setStatusMessage("Creating webhook...");
    const res = await fetch(`${BACKEND_URL}/v1/admin/external/webhooks`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        owner_user_id: webhookOwner,
        url: webhookUrl,
        events: webhookEventsSelected,
      }),
    });
    const data = await res.json();
    setWebhookResult(data);
    setStatusMessage(res.ok ? "Webhook created" : data.detail || "Create webhook failed");
  };

  const deleteWebhook = async () => {
    setStatusMessage("Disabling webhook...");
    const res = await fetch(
      `${BACKEND_URL}/v1/admin/external/webhooks/${deleteWebhookId}?owner_user_id=${deleteWebhookOwner}`,
      {
        method: "DELETE",
        headers,
      }
    );
    const data = await res.json();
    setStatusMessage(res.ok ? "Webhook disabled" : data.detail || "Delete failed");
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-50 p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        <header className="space-y-2">
          <h1 className="text-4xl font-black">External Platform Admin</h1>
          <p className="text-slate-400">Superuser console. Manage all orgs, keys, and webhooks.</p>
        </header>

        <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
          <label className="block text-sm text-slate-300">Admin Key (X-Admin-Key)</label>
          <input
            className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
            placeholder="admin key"
            value={adminKey}
            onChange={(e) => setAdminKey(e.target.value)}
          />
          <p className="text-xs text-slate-500">Required for all actions.</p>

          <label className="block text-sm text-slate-300 mt-4">Filter by Org ID (optional)</label>
          <input
            className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
            placeholder="org_xyz123 (leave blank for all orgs)"
            value={filterOrgId}
            onChange={(e) => setFilterOrgId(e.target.value)}
          />
          <p className="text-xs text-slate-500">Admin-only: scope operations to a specific organization</p>
        </div>
        </div>

        {/* API Key Management */}
        <section className="grid md:grid-cols-2 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
            <h2 className="text-xl font-bold">Create API Key</h2>
            <input
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
              placeholder="Owner user id"
              value={ownerUserId}
              onChange={(e) => setOwnerUserId(e.target.value)}
            />
            <div className="space-y-2">
              <label className="text-sm text-slate-300">Scopes</label>
              <div className="flex flex-wrap gap-2">
                {scopes.map((scope) => (
                  <label key={scope} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={selectedScopes.includes(scope)}
                      onChange={() => handleScopeToggle(scope)}
                    />
                    {scope}
                  </label>
                ))}
              </div>
            </div>
            <div className="flex gap-3 items-center">
              <label className="text-sm text-slate-300">Tier</label>
              <select
                className="rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
                value={tier}
                onChange={(e) => setTier(e.target.value)}
              >
                {tiers.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <input
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
              placeholder="Expires in days (optional)"
              value={expiresInDays}
              onChange={(e) => setExpiresInDays(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm text-slate-300">
              <input
                type="checkbox"
                checked={canaryEnabled}
                onChange={(e) => setCanaryEnabled(e.target.checked)}
              />
              <span className="font-semibold">🛡️ Canary Key (10 req/hr limit)</span>
            </label>
            <textarea
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
              placeholder="IP allowlist (comma or newline separated)"
              value={ipAllowlist}
              onChange={(e) => setIpAllowlist(e.target.value)}
            />
            <button
              className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-lg px-4 py-2"
              onClick={createKey}
            >
              Create Key
            </button>
            {createResult?.full_key && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 text-sm">
                <div className="font-semibold">Full Key (copy now):</div>
                <div className="font-mono text-emerald-300 break-all">{createResult.full_key}</div>
              </div>
            )}
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
            <h2 className="text-xl font-bold">Rotate / Revoke</h2>
            <input
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
              placeholder="Key ID"
              value={keyId}
              onChange={(e) => setKeyId(e.target.value)}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={rotatePreserve}
                onChange={(e) => setRotatePreserve(e.target.checked)}
              />
              Preserve key_id
            </label>
            <button
              className="bg-blue-500 hover:bg-blue-600 text-slate-950 font-semibold rounded-lg px-4 py-2"
              onClick={rotateKey}
            >
              Rotate Key
            </button>
            <button
              className="bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg px-4 py-2"
              onClick={revokeKey}
            >
              Revoke Key
            </button>
            {rotateResult?.full_key && (
              <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3 text-sm">
                <div className="font-semibold">New Secret (copy now):</div>
                <div className="font-mono text-blue-200 break-all">{rotateResult.full_key}</div>
              </div>
            )}
          </div>
        </section>

        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
          <h2 className="text-xl font-bold">List API Keys</h2>
          <div className="flex gap-3 flex-col md:flex-row">
            <input
              className="flex-1 rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
              placeholder="Owner user id"
              value={ownerUserId}
              onChange={(e) => setOwnerUserId(e.target.value)}
            />
            <button
              className="bg-slate-700 hover:bg-slate-600 text-white rounded-lg px-4 py-2"
              onClick={fetchKeys}
            >
              Load Keys
            </button>
          </div>
          <div className="space-y-2 text-sm">
            {listKeys.map((k) => (
              <div key={k.key_id} className="border border-slate-800 rounded-lg p-3 bg-slate-950/40">
                <div className="font-mono text-slate-200">{k.key_id}</div>
                <div className="text-slate-400">Scopes: {k.scopes?.join(", ")}</div>
                <div className="text-slate-400">Tier: {k.tier}</div>
                <div className="text-slate-500 text-xs">Last used: {k.last_used_at || "never"}</div>
              </div>
            ))}
            {!listKeys.length && <div className="text-slate-500">No keys loaded.</div>}
          </div>
        </section>

        {/* Webhook Management */}
        <section className="grid md:grid-cols-2 gap-4">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
            <h2 className="text-xl font-bold">Create Webhook</h2>
            <input
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
              placeholder="Owner user id"
              value={webhookOwner}
              onChange={(e) => setWebhookOwner(e.target.value)}
            />
            <input
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
              placeholder="Webhook URL"
              value={webhookUrl}
              onChange={(e) => setWebhookUrl(e.target.value)}
            />
            <div className="space-y-2">
              <label className="text-sm text-slate-300">Events</label>
              <div className="flex flex-wrap gap-2">
                {webhookEvents.map((evt) => (
                  <label key={evt} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={webhookEventsSelected.includes(evt)}
                      onChange={() => handleEventToggle(evt)}
                    />
                    {evt}
                  </label>
                ))}
              </div>
            </div>
            <button
              className="bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-lg px-4 py-2"
              onClick={createWebhook}
            >
              Create Webhook
            </button>
            {webhookResult?.secret && (
              <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 text-sm">
                <div className="font-semibold">Secret (copy now):</div>
                <div className="font-mono text-emerald-200 break-all">{webhookResult.secret}</div>
              </div>
            )}
          </div>

          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 space-y-3">
            <h2 className="text-xl font-bold">Disable Webhook</h2>
            <input
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
              placeholder="Webhook ID"
              value={deleteWebhookId}
              onChange={(e) => setDeleteWebhookId(e.target.value)}
            />
            <input
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
              placeholder="Owner user id"
              value={deleteWebhookOwner}
              onChange={(e) => setDeleteWebhookOwner(e.target.value)}
            />
            <button
              className="bg-red-500 hover:bg-red-600 text-white font-semibold rounded-lg px-4 py-2"
              onClick={deleteWebhook}
            >
              Disable
            </button>
          </div>
        </section>

        {statusMessage && <div className="text-sm text-slate-300">{statusMessage}</div>}
      </div>
    </div>
  );
}
