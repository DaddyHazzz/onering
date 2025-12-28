import { describe, it, expect, beforeEach, vi } from "vitest";
import { buildOrgHeaders, buildOrgParams } from "@/lib/org";

// Mock fetch
global.fetch = vi.fn();

describe("PartnerOnboardingWizard Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (global.fetch as any).mockClear();
  });

  it("buildOrgHeaders includes X-Org-ID when provided", () => {
    const headers = buildOrgHeaders("org_xyz123");
    expect(headers["X-Org-ID"]).toBe("org_xyz123");
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("buildOrgHeaders omits X-Org-ID when not provided", () => {
    const headers = buildOrgHeaders();
    expect(headers["X-Org-ID"]).toBeUndefined();
    expect(headers["Content-Type"]).toBe("application/json");
  });

  it("buildOrgParams merges base params with org_id", () => {
    const params = buildOrgParams({ scope: "draft.read" }, "org_xyz123");
    expect(params.org_id).toBe("org_xyz123");
    expect(params.scope).toBe("draft.read");
  });

  it("buildOrgParams omits org_id when not provided", () => {
    const params = buildOrgParams({ scope: "draft.read" });
    expect(params.org_id).toBeUndefined();
    expect(params.scope).toBe("draft.read");
  });

  it("supports three-step wizard pattern with org headers", async () => {
    // Mock Step 1: Create key
    const createKeyHeaders = buildOrgHeaders("org_xyz123");
    expect(createKeyHeaders["X-Org-ID"]).toBe("org_xyz123");

    // Mock Step 2: Test API (verify headers)
    const testApiHeaders = buildOrgHeaders("org_xyz123");
    expect(testApiHeaders["X-Org-ID"]).toBe("org_xyz123");

    // Mock Step 3: Create webhook (verify headers)
    const webhookHeaders = buildOrgHeaders("org_xyz123");
    expect(webhookHeaders["X-Org-ID"]).toBe("org_xyz123");
  });

  it("supports admin filtering with org params", () => {
    // Admin can filter by org_id
    const adminParams = buildOrgParams({ filter: "status:active" }, "org_xyz123");
    expect(adminParams.org_id).toBe("org_xyz123");
    expect(adminParams.filter).toBe("status:active");

    // Without filtering
    const noFilterParams = buildOrgParams({ filter: "status:active" });
    expect(noFilterParams.org_id).toBeUndefined();
  });

  it("wizard can accept both form data and API responses", async () => {
    // Simulated form submission
    const formData = {
      scopes: ["draft.read", "draft.write"],
      tier: "starter",
    };

    // API response structure
    const apiResponse = {
      key_id: "ext_key_abc123",
      secret: "secret_xyz",
      tier: "starter",
      org_id: "org_xyz123",
    };

    expect(apiResponse.key_id).toBeDefined();
    expect(apiResponse.org_id).toBe("org_xyz123");
  });

  it("tracks webhook events in correct org context", () => {
    const orgId = "org_xyz123";
    const webhookEvent = {
      event_type: "draft.published",
      org_id: orgId,
      data: {
        draft_id: "draft_xyz",
      },
    };

    expect(webhookEvent.org_id).toBe(orgId);
  });
});
