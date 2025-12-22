/**
 * src/__tests__/analytics-routes.spec.ts
 * Phase 3.4 analytics API route handler tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NextRequest } from "next/server";
import { GET as getLeaderboard } from "../app/api/analytics/leaderboard/route";
import { GET as getDraftAnalytics } from "../app/api/collab/drafts/[draftId]/analytics/route";

// Mock Clerk
vi.mock("@clerk/nextjs/server", () => ({
  currentUser: vi.fn(),
}));

import { currentUser } from "@clerk/nextjs/server";

describe("Analytics Route Handlers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("GET /api/analytics/leaderboard", () => {
    it("should return 401 when user is not authenticated", async () => {
      vi.mocked(currentUser).mockResolvedValue(null);

      const req = new NextRequest(
        "http://localhost:3000/api/analytics/leaderboard?metric=collaboration"
      );
      const response = await getLeaderboard(req);
      const data = await response.json();

      expect(response.status).toBe(401);
      expect(data.error).toBe("Unauthorized");
    });

    it("should return 400 when metric is invalid", async () => {
      vi.mocked(currentUser).mockResolvedValue({ id: "user-123" } as any);

      const req = new NextRequest(
        "http://localhost:3000/api/analytics/leaderboard?metric=invalid"
      );
      const response = await getLeaderboard(req);
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toContain("Invalid metric type");
    });

    it("should successfully proxy to backend with valid request", async () => {
      vi.mocked(currentUser).mockResolvedValue({ id: "user-123" } as any);

      const mockBackendResponse = {
        success: true,
        data: {
          metric_type: "collaboration",
          entries: [
            {
              position: 1,
              user_id: "user-1",
              display_name: "Alice",
              avatar_url: null,
              metric_value: 100,
              metric_label: "15 segments",
              insight: "Leading by example!",
            },
          ],
          computed_at: new Date().toISOString(),
          message: "Community highlights: creators shaping work together",
        },
      };

      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockBackendResponse,
      } as any);

      const req = new NextRequest(
        "http://localhost:3000/api/analytics/leaderboard?metric=collaboration"
      );
      const response = await getLeaderboard(req);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.data.metric_type).toBe("collaboration");
    });

    it("should pass optional now parameter to backend", async () => {
      vi.mocked(currentUser).mockResolvedValue({ id: "user-123" } as any);

      const mockBackendResponse = {
        success: true,
        data: {
          metric_type: "collaboration",
          entries: [],
          computed_at: "2025-12-21T15:30:00Z",
          message: "Test message",
        },
      };

      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockBackendResponse,
      } as any);

      const req = new NextRequest(
        "http://localhost:3000/api/analytics/leaderboard?metric=collaboration&now=2025-12-21T15:30:00Z"
      );
      await getLeaderboard(req);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("now=2025-12-21T15%3A30%3A00Z"),
        expect.any(Object)
      );
    });

    it("should reject response with forbidden comparative language", async () => {
      vi.mocked(currentUser).mockResolvedValue({ id: "user-123" } as any);

      const mockBackendResponse = {
        success: true,
        data: {
          metric_type: "collaboration",
          entries: [
            {
              position: 1,
              user_id: "user-1",
              display_name: "Alice",
              avatar_url: null,
              metric_value: 100,
              metric_label: "15 segments",
              insight: "You're falling behind others!", // Forbidden
            },
          ],
          computed_at: new Date().toISOString(),
          message: "Test message",
        },
      };

      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockBackendResponse,
      } as any);

      const req = new NextRequest(
        "http://localhost:3000/api/analytics/leaderboard?metric=collaboration"
      );
      const response = await getLeaderboard(req);
      const data = await response.json();

      expect(response.status).toBe(500);
      expect(data.error).toContain("forbidden comparative language");
    });

    it("should default to collaboration metric when metric not specified", async () => {
      vi.mocked(currentUser).mockResolvedValue({ id: "user-123" } as any);

      const mockBackendResponse = {
        success: true,
        data: {
          metric_type: "collaboration",
          entries: [],
          computed_at: new Date().toISOString(),
          message: "Test message",
        },
      };

      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockBackendResponse,
      } as any);

      const req = new NextRequest(
        "http://localhost:3000/api/analytics/leaderboard"
      );
      await getLeaderboard(req);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("metric=collaboration"),
        expect.any(Object)
      );
    });
  });

  describe("GET /api/collab/drafts/[draftId]/analytics", () => {
    it("should return 401 when user is not authenticated", async () => {
      vi.mocked(currentUser).mockResolvedValue(null);

      const req = new NextRequest(
        "http://localhost:3000/api/collab/drafts/draft-123/analytics"
      );
      const response = await getDraftAnalytics(req, {
        params: { draftId: "draft-123" },
      });
      const data = await response.json();

      expect(response.status).toBe(401);
      expect(data.error).toBe("Unauthorized");
    });

    it("should return 400 when draftId is missing", async () => {
      vi.mocked(currentUser).mockResolvedValue({ id: "user-123" } as any);

      const req = new NextRequest(
        "http://localhost:3000/api/collab/drafts//analytics"
      );
      const response = await getDraftAnalytics(req, { params: { draftId: "" } });
      const data = await response.json();

      expect(response.status).toBe(400);
      expect(data.error).toBe("Missing draftId");
    });

    it("should successfully proxy to backend with valid request", async () => {
      vi.mocked(currentUser).mockResolvedValue({ id: "user-123" } as any);

      const mockBackendResponse = {
        success: true,
        data: {
          draft_id: "draft-123",
          views: 10,
          shares: 5,
          segments_count: 3,
          contributors_count: 2,
          ring_passes_count: 4,
          last_activity_at: new Date().toISOString(),
          computed_at: new Date().toISOString(),
        },
      };

      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockBackendResponse,
      } as any);

      const req = new NextRequest(
        "http://localhost:3000/api/collab/drafts/draft-123/analytics"
      );
      const response = await getDraftAnalytics(req, {
        params: { draftId: "draft-123" },
      });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.success).toBe(true);
      expect(data.data.draft_id).toBe("draft-123");
      expect(data.data.views).toBe(10);
    });

    it("should pass optional now parameter to backend", async () => {
      vi.mocked(currentUser).mockResolvedValue({ id: "user-123" } as any);

      const mockBackendResponse = {
        success: true,
        data: {
          draft_id: "draft-123",
          views: 0,
          shares: 0,
          segments_count: 1,
          contributors_count: 1,
          ring_passes_count: 0,
          last_activity_at: null,
          computed_at: "2025-12-21T15:30:00Z",
        },
      };

      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => mockBackendResponse,
      } as any);

      const req = new NextRequest(
        "http://localhost:3000/api/collab/drafts/draft-123/analytics?now=2025-12-21T15:30:00Z"
      );
      await getDraftAnalytics(req, { params: { draftId: "draft-123" } });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining("now=2025-12-21T15%3A30%3A00Z"),
        expect.any(Object)
      );
    });

    it("should validate response shape with Zod schema", async () => {
      vi.mocked(currentUser).mockResolvedValue({ id: "user-123" } as any);

      const invalidBackendResponse = {
        success: true,
        data: {
          draft_id: "draft-123",
          views: "invalid", // Should be number
          shares: 0,
          segments_count: 1,
          contributors_count: 1,
          ring_passes_count: 0,
          last_activity_at: null,
          computed_at: new Date().toISOString(),
        },
      };

      vi.mocked(global.fetch).mockResolvedValue({
        ok: true,
        json: async () => invalidBackendResponse,
      } as any);

      const req = new NextRequest(
        "http://localhost:3000/api/collab/drafts/draft-123/analytics"
      );
      const response = await getDraftAnalytics(req, {
        params: { draftId: "draft-123" },
      });

      expect(response.status).toBe(500);
    });

    it("should handle backend errors gracefully", async () => {
      vi.mocked(currentUser).mockResolvedValue({ id: "user-123" } as any);

      vi.mocked(global.fetch).mockResolvedValue({
        ok: false,
        statusText: "Not Found",
        status: 404,
      } as any);

      const req = new NextRequest(
        "http://localhost:3000/api/collab/drafts/draft-123/analytics"
      );
      const response = await getDraftAnalytics(req, {
        params: { draftId: "draft-123" },
      });
      const data = await response.json();

      expect(response.status).toBe(404);
      expect(data.error).toContain("Backend error");
    });
  });
});
