import { describe, it, expect, beforeEach, vi } from "vitest";
import { buildOrgHeaders, buildOrgParams, isPartner, isAdmin } from "@/lib/org";

describe("Org-Aware Utilities", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("buildOrgHeaders Utility", () => {
    it("includes X-Org-ID when org ID provided", () => {
      const headers = buildOrgHeaders("org_xyz123");
      expect(headers["X-Org-ID"]).toBe("org_xyz123");
    });

    it("excludes X-Org-ID when org ID is undefined", () => {
      const headers = buildOrgHeaders(undefined);
      expect(headers["X-Org-ID"]).toBeUndefined();
    });

    it("includes base headers", () => {
      const headers = buildOrgHeaders("org_xyz123");
      expect(headers["Content-Type"]).toBe("application/json");
    });
  });

  describe("buildOrgParams Utility", () => {
    it("adds org_id to params when org ID provided", () => {
      const params = buildOrgParams({ foo: "bar" }, "org_xyz123");
      expect(params.org_id).toBe("org_xyz123");
      expect(params.foo).toBe("bar");
    });

    it("excludes org_id when org ID is undefined", () => {
      const params = buildOrgParams({ foo: "bar" }, undefined);
      expect(params.org_id).toBeUndefined();
      expect(params.foo).toBe("bar");
    });

    it("handles empty base params", () => {
      const params = buildOrgParams({}, "org_xyz123");
      expect(params.org_id).toBe("org_xyz123");
    });

    it("merges multiple base params with org_id", () => {
      const params = buildOrgParams({ filter: "active", limit: "10" }, "org_xyz123");
      expect(params.org_id).toBe("org_xyz123");
      expect(params.filter).toBe("active");
      expect(params.limit).toBe("10");
    });
  });

  describe("isPartner and isAdmin Utilities", () => {
    it("isPartner identifies partner role from publicMetadata", () => {
      const user = { publicMetadata: { role: "partner" } };
      expect(isPartner(user)).toBe(true);
    });

    it("isPartner returns false for non-partners", () => {
      const user = { publicMetadata: { role: "user" } };
      expect(isPartner(user)).toBe(false);
    });

    it("isPartner returns false when publicMetadata missing", () => {
      const user = { publicMetadata: undefined };
      expect(isPartner(user)).toBe(false);
    });

    it("isAdmin identifies admin role from publicMetadata", () => {
      const user = { publicMetadata: { role: "admin" } };
      expect(isAdmin(user)).toBe(true);
    });

    it("isAdmin returns false for non-admins", () => {
      const user = { publicMetadata: { role: "user" } };
      expect(isAdmin(user)).toBe(false);
    });

    it("isAdmin returns false when publicMetadata missing", () => {
      const user = { publicMetadata: undefined };
      expect(isAdmin(user)).toBe(false);
    });

    it("handles null user gracefully", () => {
      expect(isPartner(null)).toBe(false);
      expect(isAdmin(null)).toBe(false);
    });

    it("supports checking both roles", () => {
      const adminUser = { publicMetadata: { role: "admin" } };
      const partnerUser = { publicMetadata: { role: "partner" } };

      expect(isAdmin(adminUser)).toBe(true);
      expect(isPartner(adminUser)).toBe(false);

      expect(isPartner(partnerUser)).toBe(true);
      expect(isAdmin(partnerUser)).toBe(false);
    });
  });

  describe("Org-Aware API Patterns", () => {
    it("supports partner API calls with org scoping", () => {
      const orgId = "org_xyz123";
      const headers = buildOrgHeaders(orgId);

      expect(headers["X-Org-ID"]).toBe(orgId);
      expect(headers["Content-Type"]).toBe("application/json");
    });

    it("supports admin filtering across orgs", () => {
      // Admin can filter by org_id
      const params = buildOrgParams({ status: "active" }, "org_xyz123");
      expect(params.org_id).toBe("org_xyz123");

      // Or leave unfiltered
      const unfilteredParams = buildOrgParams({ status: "active" });
      expect(unfilteredParams.org_id).toBeUndefined();
    });

    it("supports single-user mode without org", () => {
      const headers = buildOrgHeaders();
      const params = buildOrgParams({});

      expect(headers["X-Org-ID"]).toBeUndefined();
      expect(params.org_id).toBeUndefined();
    });
  });

  describe("Wizard Integration Patterns", () => {
    it("creates key API call with org headers", () => {
      const orgId = "org_xyz123";
      const headers = buildOrgHeaders(orgId);

      // Simulate API call structure
      const apiCall = {
        method: "POST",
        url: "/api/external/keys",
        headers: headers,
        body: JSON.stringify({ scopes: ["draft.read"] }),
      };

      expect(apiCall.headers["X-Org-ID"]).toBe(orgId);
    });

    it("test API call with org context", () => {
      const orgId = "org_xyz123";
      const headers = buildOrgHeaders(orgId);

      const apiCall = {
        method: "GET",
        url: "/v1/external/me",
        headers: headers,
      };

      expect(apiCall.headers["X-Org-ID"]).toBe(orgId);
    });

    it("webhook creation with org scoping", () => {
      const orgId = "org_xyz123";
      const headers = buildOrgHeaders(orgId);

      const apiCall = {
        method: "POST",
        url: "/api/external/webhooks",
        headers: headers,
        body: JSON.stringify({
          url: "https://example.com/webhook",
          events: ["draft.published"],
        }),
      };

      expect(apiCall.headers["X-Org-ID"]).toBe(orgId);
    });
  });
});
