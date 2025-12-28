"use client";

import { useOrganization, useClerk } from "@clerk/nextjs";
import { useState } from "react";

/**
 * OrgBadge Component
 * Shows current org name and provides org switching UI
 * Gracefully hidden if no org present (single-user mode)
 */
export function OrgBadge() {
  const { organization, organizations, setActive } = useOrganization();
  const { user } = useClerk();
  const [isOpen, setIsOpen] = useState(false);

  // Don't render if no org (single-user mode)
  if (!organization) {
    return null;
  }

  const handleSwitchOrg = async (orgId: string) => {
    await setActive({ organization: orgId });
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 border border-slate-700 text-sm text-slate-200"
      >
        <span className="font-semibold">🏢 {organization.name}</span>
        {(organizations?.length ?? 0) > 1 && (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
          </svg>
        )}
      </button>

      {isOpen && organizations && organizations.length > 1 && (
        <div className="absolute top-full mt-2 right-0 bg-slate-900 border border-slate-700 rounded-lg shadow-lg z-10 min-w-48">
          {organizations.map((org) => (
            <button
              key={org.id}
              onClick={() => handleSwitchOrg(org.id)}
              className={`w-full text-left px-4 py-2 hover:bg-slate-800 ${
                org.id === organization.id ? "bg-slate-700" : ""
              } text-sm text-slate-200`}
            >
              {org.name}
              {org.id === organization.id && " ✓"}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
export default OrgBadge;