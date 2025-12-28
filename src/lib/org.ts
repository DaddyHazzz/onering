/**
 * Org-aware utilities for SaaS platform
 * Handles org_id threading through API calls
 */

import { useOrganization, useUser } from "@clerk/nextjs";

/**
 * Get active org ID from Clerk context
 * Returns undefined if no org present (single-user mode)
 */
export function useActiveOrgId(): string | undefined {
  const { organization } = useOrganization();
  return organization?.id;
}

/**
 * Build org-aware API headers
 * Includes X-Org-ID if org is present
 */
export function buildOrgHeaders(orgId?: string): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (orgId) {
    headers["X-Org-ID"] = orgId;
  }

  return headers;
}

/**
 * Build org-aware query params
 * Merges base params with org_id if org is present
 */
export function buildOrgParams(
  baseParams: Record<string, string> = {},
  orgId?: string
): Record<string, string> {
  const params = { ...baseParams };

  if (orgId) {
    params["org_id"] = orgId;
  }

  return params;
}

/**
 * Check if user has partner role in current org
 * Used for routing to partner console vs admin console
 */
export function isPartner(user?: any): boolean {
  if (!user?.publicMetadata) return false;
  const role = user.publicMetadata.role;
  return role === "partner";
}

/**
 * Check if user has admin role (super admin)
 * Only super admins can access /admin/external
 */
export function isAdmin(user?: any): boolean {
  if (!user?.publicMetadata) return false;
  const role = user.publicMetadata.role;
  return role === "admin";
}
