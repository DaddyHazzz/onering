"use client";

import { useState } from "react";
import { useActiveOrgId, buildOrgHeaders } from "@/lib/org";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

type OnboardingStep = "create_key" | "test_api" | "create_webhook";

interface CreateKeyResult {
  key_id: string;
  full_key: string;
  tier: string;
}

interface TestApiResponse {
  user_id: string;
  org_id?: string;
  rate_limit: number;
  canary_mode: boolean;
}

/**
 * PartnerOnboardingWizard Component
 * 3-step flow: Create Key → Test API → Create Webhook
 */
export function PartnerOnboardingWizard() {
  const orgId = useActiveOrgId();
  const [step, setStep] = useState<OnboardingStep>("create_key");
  const [adminKey, setAdminKey] = useState("");

  // Step 1: Create Key
  const [scopes, setScopes] = useState<string[]>(["read:rings"]);
  const [tier, setTier] = useState("free");
  const [createKeyResult, setCreateKeyResult] = useState<CreateKeyResult | null>(null);
  const [createKeyError, setCreateKeyError] = useState<string>("");

  // Step 2: Test API
  const [apiKey, setApiKey] = useState("");
  const [testApiResult, setTestApiResult] = useState<TestApiResponse | null>(null);
  const [testApiError, setTestApiError] = useState<string>("");
  const [testApiResponse, setTestApiResponse] = useState<string>("");

  // Step 3: Create Webhook
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookEvents, setWebhookEvents] = useState<string[]>(["draft.published"]);
  const [webhookError, setWebhookError] = useState<string>("");
  const [webhookResult, setWebhookResult] = useState<any>(null);

  const handleScopeToggle = (scope: string) => {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    );
  };

  const handleEventToggle = (event: string) => {
    setWebhookEvents((prev) =>
      prev.includes(event) ? prev.filter((e) => e !== event) : [...prev, event]
    );
  };

  const createKey = async () => {
    setCreateKeyError("");
    const headers = buildOrgHeaders(orgId);
    headers["X-Admin-Key"] = adminKey;

    try {
      const res = await fetch(`${BACKEND_URL}/v1/admin/external/keys`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          owner_user_id: undefined, // Uses current user from context
          scopes,
          tier,
          canary_enabled: false,
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to create key");
      }

      const data = await res.json();
      setCreateKeyResult(data);
      setApiKey(data.full_key);
      // Auto-advance to test step
      setTimeout(() => setStep("test_api"), 500);
    } catch (err: any) {
      setCreateKeyError(err.message);
    }
  };

  const testApi = async () => {
    setTestApiError("");
    setTestApiResponse("");

    try {
      const res = await fetch(`${BACKEND_URL}/v1/external/me`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${apiKey}`,
          ...buildOrgHeaders(orgId),
        },
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "API test failed");
      }

      const data = await res.json();
      setTestApiResult(data);
      setTestApiResponse(JSON.stringify(data, null, 2));
      // Auto-advance to webhook step
      setTimeout(() => setStep("create_webhook"), 500);
    } catch (err: any) {
      setTestApiError(err.message);
    }
  };

  const createWebhook = async () => {
    setWebhookError("");

    try {
      const headers = buildOrgHeaders(orgId);
      headers["X-Admin-Key"] = adminKey;

      const res = await fetch(`${BACKEND_URL}/v1/admin/external/webhooks`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          owner_user_id: undefined, // Uses current user
          url: webhookUrl,
          events: webhookEvents,
        }),
      });

      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || "Failed to create webhook");
      }

      const data = await res.json();
      setWebhookResult(data);
    } catch (err: any) {
      setWebhookError(err.message);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-6">
      {/* Progress Bar */}
      <div className="flex items-center gap-4">
        {(["create_key", "test_api", "create_webhook"] as const).map((s, idx) => (
          <div key={s} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                step === s
                  ? "bg-emerald-500 text-slate-950"
                  : idx < (["create_key", "test_api", "create_webhook"] as const).indexOf(step)
                  ? "bg-emerald-700 text-slate-50"
                  : "bg-slate-700 text-slate-400"
              }`}
            >
              {idx + 1}
            </div>
            {idx < 2 && <div className="w-8 h-0.5 bg-slate-700" />}
          </div>
        ))}
      </div>

      {/* Step 1: Create Key */}
      {step === "create_key" && (
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-2xl font-bold">Step 1: Create API Key</h2>
          <p className="text-slate-400 text-sm">
            Generate your first API key to authenticate with the OneRing External API.
          </p>

          {createKeyResult ? (
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 space-y-3">
              <div className="text-emerald-300 font-semibold">✓ Key Created Successfully</div>
              <div className="bg-slate-950 rounded px-3 py-2 border border-slate-800">
                <div className="text-xs text-slate-400 mb-1">Full Key (copy now):</div>
                <div className="font-mono text-sm text-emerald-300 break-all">{createKeyResult.full_key}</div>
              </div>
              <button
                onClick={() => copyToClipboard(createKeyResult.full_key)}
                className="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1 rounded"
              >
                📋 Copy to Clipboard
              </button>
              <p className="text-xs text-slate-500">Store this securely. It won't be shown again.</p>
            </div>
          ) : (
            <>
              <div className="space-y-3">
                <div>
                  <label className="text-sm text-slate-300">Admin Key</label>
                  <input
                    type="password"
                    className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-50"
                    placeholder="X-Admin-Key for verification"
                    value={adminKey}
                    onChange={(e) => setAdminKey(e.target.value)}
                  />
                </div>

                <div>
                  <label className="text-sm text-slate-300 block mb-2">Scopes</label>
                  <div className="space-y-2">
                    {["read:rings", "read:drafts", "read:ledger"].map((scope) => (
                      <label key={scope} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={scopes.includes(scope)}
                          onChange={() => handleScopeToggle(scope)}
                        />
                        {scope}
                      </label>
                    ))}
                  </div>
                </div>

                <div>
                  <label className="text-sm text-slate-300 block mb-2">Tier</label>
                  <select
                    className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2"
                    value={tier}
                    onChange={(e) => setTier(e.target.value)}
                  >
                    <option value="free">Free (tier 1)</option>
                    <option value="pro">Pro (tier 2)</option>
                    <option value="enterprise">Enterprise (tier 3)</option>
                  </select>
                </div>
              </div>

              {createKeyError && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-300 text-sm">
                  {createKeyError}
                </div>
              )}

              <button
                onClick={createKey}
                className="w-full bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-lg px-4 py-2"
              >
                Create Key
              </button>
            </>
          )}
        </section>
      )}

      {/* Step 2: Test API */}
      {step === "test_api" && (
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-2xl font-bold">Step 2: Test API Connection</h2>
          <p className="text-slate-400 text-sm">
            Verify your key works by calling the /v1/external/me endpoint.
          </p>

          <div className="bg-slate-950 rounded-lg border border-slate-800 p-4 space-y-3">
            <div className="text-sm text-slate-300 font-mono">
              Curl command:
            </div>
            <div className="bg-slate-900 rounded px-3 py-2 border border-slate-700 overflow-x-auto">
              <pre className="text-xs text-slate-400">
                {`curl -X GET http://localhost:8000/v1/external/me \\
  -H "Authorization: Bearer ${apiKey || "YOUR_API_KEY"}" \\
  -H "X-Org-ID: ${orgId || "org_id"}"`}
              </pre>
            </div>
            <button
              onClick={() =>
                copyToClipboard(
                  `curl -X GET http://localhost:8000/v1/external/me -H "Authorization: Bearer ${apiKey}" -H "X-Org-ID: ${orgId}"`
                )
              }
              className="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1 rounded"
            >
              📋 Copy Curl
            </button>
          </div>

          <div>
            <label className="text-sm text-slate-300 block mb-2">Paste response here:</label>
            <textarea
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-50 font-mono text-xs h-24"
              placeholder='{"user_id": "...", "rate_limit": 1000}'
              value={testApiResponse}
              onChange={(e) => setTestApiResponse(e.target.value)}
            />
          </div>

          {testApiResult && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3">
              <div className="text-emerald-300 text-sm font-semibold">✓ API Test Passed</div>
              <div className="text-slate-400 text-xs mt-1">
                User: {testApiResult.user_id} | Rate Limit: {testApiResult.rate_limit} req/hr
              </div>
            </div>
          )}

          {testApiError && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-300 text-sm">
              {testApiError}
            </div>
          )}

          <button
            onClick={testApi}
            className="w-full bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-lg px-4 py-2"
          >
            Run API Test
          </button>
        </section>
      )}

      {/* Step 3: Create Webhook */}
      {step === "create_webhook" && (
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-2xl font-bold">Step 3: Create Webhook Subscription</h2>
          <p className="text-slate-400 text-sm">
            Set up webhooks to receive real-time events from OneRing.
          </p>

          <div className="space-y-3">
            <div>
              <label className="text-sm text-slate-300 block mb-2">Webhook URL</label>
              <input
                type="url"
                className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-slate-50"
                placeholder="https://example.com/webhook"
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
              />
            </div>

            <div>
              <label className="text-sm text-slate-300 block mb-2">Events</label>
              <div className="space-y-2">
                {["draft.published", "ring.earned", "enforcement.failed"].map((event) => (
                  <label key={event} className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={webhookEvents.includes(event)}
                      onChange={() => handleEventToggle(event)}
                    />
                    {event}
                  </label>
                ))}
              </div>
            </div>

            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
              <div className="text-blue-300 text-sm font-semibold">💡 Testing Webhooks?</div>
              <p className="text-blue-200 text-xs mt-1">
                Use{" "}
                <code className="bg-slate-800 px-1 rounded">webhook.site</code> for temporary URL
              </p>
            </div>
          </div>

          {webhookResult && (
            <div className="bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-4 space-y-3">
              <div className="text-emerald-300 font-semibold">✓ Webhook Created</div>
              <div className="text-slate-300 text-sm">
                Webhook ID: <code className="bg-slate-800 px-1 rounded">{webhookResult.webhook_id}</code>
              </div>
              <div className="bg-slate-950 rounded px-3 py-2 border border-slate-800">
                <div className="text-xs text-slate-400 mb-1">Secret (store securely):</div>
                <div className="font-mono text-sm text-emerald-300">{webhookResult.secret}</div>
              </div>
              <button
                onClick={() => copyToClipboard(webhookResult.secret)}
                className="text-xs bg-slate-800 hover:bg-slate-700 px-3 py-1 rounded"
              >
                📋 Copy Secret
              </button>
              <p className="text-xs text-slate-500">
                Use this secret to verify webhook signatures. See{" "}
                <a href="/external-api-consumer-guide" className="text-emerald-400 hover:underline">
                  consumer guide
                </a>{" "}
                for details.
              </p>
            </div>
          )}

          {webhookError && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-300 text-sm">
              {webhookError}
            </div>
          )}

          <button
            onClick={createWebhook}
            className="w-full bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-semibold rounded-lg px-4 py-2"
          >
            Create Webhook
          </button>

          {webhookResult && (
            <div className="text-center pt-4">
              <p className="text-slate-400 text-sm">
                🎉 Onboarding complete! Start using the External API.
              </p>
              <a href="/external-api-consumer-guide" className="text-emerald-400 hover:underline text-sm">
                View full consumer guide →
              </a>
            </div>
          )}
        </section>
      )}
    </div>
  );
}
export default PartnerOnboardingWizard;