"use client";

import { useUser } from "@clerk/nextjs";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { OrgBadge } from "@/components/OrgBadge";
import { PartnerOnboardingWizard } from "@/components/PartnerOnboardingWizard";
import { useActiveOrgId } from "@/lib/org";

/**
 * Partner Console for External API Management
 * Scoped to org - partners can only manage their own keys and webhooks
 * 
 * Differences from /admin/external:
 * - Partner can only see/manage their own org's keys
 * - No system-wide metrics
 * - Onboarding-focused UX
 * - Limited to partner tier features
 */
export default function PartnerExternalPage() {
  const { user, isLoaded } = useUser();
  const router = useRouter();
  const orgId = useActiveOrgId();

  useEffect(() => {
    if (isLoaded && !user) {
      router.push("/");
    }
  }, [isLoaded, user, router]);

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
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Header with Org Badge */}
        <header className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-black">Partner Console</h1>
            <p className="text-slate-400 mt-1">Manage your organization's External API integration</p>
          </div>
          <OrgBadge />
        </header>

        {!orgId && (
          <div className="bg-blue-500/10 border border-blue-500/30 rounded-xl p-4">
            <p className="text-blue-300 text-sm">
              💡 Single-user mode detected. Create an organization in settings to enable team features.
            </p>
          </div>
        )}

        {/* Onboarding Wizard */}
        <PartnerOnboardingWizard />

        {/* Documentation Links */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
          <h2 className="text-xl font-bold">Resources</h2>
          <div className="grid md:grid-cols-2 gap-4">
            <a
              href="/docs/external-api-consumer-guide"
              className="bg-slate-800 hover:bg-slate-700 rounded-lg p-4 text-sm text-slate-300"
            >
              <div className="font-semibold text-emerald-300">📚 Consumer Guide</div>
              <p className="text-xs text-slate-400 mt-1">Full API reference and examples</p>
            </a>
            <a
              href="/docs/webhook-signing"
              className="bg-slate-800 hover:bg-slate-700 rounded-lg p-4 text-sm text-slate-300"
            >
              <div className="font-semibold text-emerald-300">🔐 Webhook Signing</div>
              <p className="text-xs text-slate-400 mt-1">How to verify webhook signatures</p>
            </a>
            <a
              href="/support"
              className="bg-slate-800 hover:bg-slate-700 rounded-lg p-4 text-sm text-slate-300"
            >
              <div className="font-semibold text-emerald-300">💬 Support</div>
              <p className="text-xs text-slate-400 mt-1">Contact support or view FAQs</p>
            </a>
            <a
              href="/docs/rate-limits"
              className="bg-slate-800 hover:bg-slate-700 rounded-lg p-4 text-sm text-slate-300"
            >
              <div className="font-semibold text-emerald-300">⚡ Rate Limits</div>
              <p className="text-xs text-slate-400 mt-1">Understand quotas for your tier</p>
            </a>
          </div>
        </section>
      </div>
    </div>
  );
}
