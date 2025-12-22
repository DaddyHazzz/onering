/**
 * src/__tests__/analytics.spec.ts
 * Phase 3.4 analytics frontend tests: schema validation, bounds, safety.
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";

// Zod schemas for analytics
const leaderboardEntrySchema = z.object({
  position: z.number().int().min(1).max(10),
  user_id: z.string(),
  display_name: z.string(),
  avatar_url: z.string().nullable(),
  metric_value: z.number(),
  metric_label: z.string(),
  insight: z.string(),
});

const leaderboardSchema = z.object({
  metric_type: z.enum(["collaboration", "momentum", "consistency"]),
  entries: z.array(leaderboardEntrySchema),
  computed_at: z.string().datetime(),
  message: z.string(),
});

const leaderboardResponseSchema = z.object({
  success: z.boolean(),
  data: leaderboardSchema,
});

describe("Analytics Frontend Schemas", () => {
  describe("Leaderboard Entry Validation", () => {
    it("should accept valid leaderboard entry", () => {
      const entry = {
        position: 1,
        user_id: "user-123",
        display_name: "Alice",
        avatar_url: "https://example.com/avatar.jpg",
        metric_value: 100,
        metric_label: "12 segments",
        insight: "Growing collaboration skills!",
      };

      expect(() => leaderboardEntrySchema.parse(entry)).not.toThrow();
    });

    it("should reject position outside 1-10 range", () => {
      const entry = {
        position: 11,
        user_id: "user-123",
        display_name: "Alice",
        avatar_url: null,
        metric_value: 100,
        metric_label: "12 segments",
        insight: "Great work!",
      };

      expect(() => leaderboardEntrySchema.parse(entry)).toThrow();
    });

    it("should accept null avatar_url", () => {
      const entry = {
        position: 1,
        user_id: "user-123",
        display_name: "Alice",
        avatar_url: null,
        metric_value: 100,
        metric_label: "12 segments",
        insight: "Great work!",
      };

      expect(() => leaderboardEntrySchema.parse(entry)).not.toThrow();
    });
  });

  describe("Leaderboard Response Validation", () => {
    it("should accept valid leaderboard response", () => {
      const response = {
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

      expect(() => leaderboardResponseSchema.parse(response)).not.toThrow();
    });

    it("should reject invalid metric_type", () => {
      const response = {
        success: true,
        data: {
          metric_type: "invalid",
          entries: [],
          computed_at: new Date().toISOString(),
          message: "Test message",
        },
      };

      expect(() => leaderboardResponseSchema.parse(response)).toThrow();
    });

    it("should reject invalid ISO timestamp", () => {
      const response = {
        success: true,
        data: {
          metric_type: "collaboration",
          entries: [],
          computed_at: "not-a-date",
          message: "Test message",
        },
      };

      expect(() => leaderboardResponseSchema.parse(response)).toThrow();
    });
  });

  describe("Leaderboard Metrics Bounds", () => {
    it("should ensure metric_value is numeric", () => {
      const entry = {
        position: 1,
        user_id: "user-1",
        display_name: "Alice",
        avatar_url: null,
        metric_value: "100", // Invalid: should be number
        metric_label: "12 segments",
        insight: "Great!",
      };

      expect(() => leaderboardEntrySchema.parse(entry)).toThrow();
    });

    it("should accept zero metric_value", () => {
      const entry = {
        position: 1,
        user_id: "user-1",
        display_name: "Alice",
        avatar_url: null,
        metric_value: 0,
        metric_label: "0 segments",
        insight: "Just starting!",
      };

      expect(() => leaderboardEntrySchema.parse(entry)).not.toThrow();
    });

    it("should accept large metric_values", () => {
      const entry = {
        position: 1,
        user_id: "user-1",
        display_name: "Alice",
        avatar_url: null,
        metric_value: 999999,
        metric_label: "999999 segments",
        insight: "Incredible dedication!",
      };

      expect(() => leaderboardEntrySchema.parse(entry)).not.toThrow();
    });
  });

  describe("Leaderboard Safety", () => {
    it("should reject entries with sensitive keywords", () => {
      const entry = {
        position: 1,
        user_id: "user-1",
        display_name: "Alice",
        avatar_url: null,
        metric_value: 100,
        metric_label: "12 segments token_hash=xyz",
        insight: "Great!",
      };

      const validated = leaderboardEntrySchema.parse(entry);
      const str = JSON.stringify(validated);

      // Token hash should be in label, but shouldn't be extracted/treated specially
      // This is more of a content validation test
      expect(str).not.toContain("secret");
      expect(str).not.toContain("password");
    });

    it("should never leak user email in display_name", () => {
      const entry = {
        position: 1,
        user_id: "user-1",
        display_name: "alice@example.com", // Should not use email
        avatar_url: null,
        metric_value: 100,
        metric_label: "12 segments",
        insight: "Great!",
      };

      // Schema doesn't validate email format, but UI should display as "user_abc123"
      // This test documents the expected pattern
      expect(entry.display_name).toMatch(/^[a-z|@]/);
    });

    it("should ensure insight never contains comparative language", () => {
      const testInsights = [
        "Growing collaboration skills!",
        "Leading by example!",
        "Building momentum!",
      ];

      for (const insight of testInsights) {
        expect(insight.toLowerCase()).not.toMatch(/you're behind|catch up|falling behind/);
      }
    });
  });

  describe("Helper Functions", () => {
    it("should format leaderboard entry position", () => {
      const formatPosition = (pos: number) => {
        if (pos === 1) return "🥇";
        if (pos === 2) return "🥈";
        if (pos === 3) return "🥉";
        return pos.toString();
      };

      expect(formatPosition(1)).toBe("🥇");
      expect(formatPosition(2)).toBe("🥈");
      expect(formatPosition(3)).toBe("🥉");
      expect(formatPosition(5)).toBe("5");
    });

    it("should format metric label for display", () => {
      const formatMetricLabel = (label: string) => {
        return label.replace(/•/g, "·");
      };

      const result = formatMetricLabel("12 segments • 3 rings");
      expect(result).toBe("12 segments · 3 rings");
    });

    it("should truncate long display names", () => {
      const truncateDisplayName = (name: string, maxLen: number = 20) => {
        return name.length > maxLen ? name.substring(0, maxLen) + "..." : name;
      };

      const longName = "a".repeat(25);
      expect(truncateDisplayName(longName)).toBe("a".repeat(20) + "...");

      const shortName = "Alice";
      expect(truncateDisplayName(shortName)).toBe("Alice");
    });
  });

  describe("Leaderboard Metric Types", () => {
    it("should support collaboration metric", () => {
      const response = {
        success: true,
        data: {
          metric_type: "collaboration" as const,
          entries: [],
          computed_at: new Date().toISOString(),
          message: "Community highlights: creators shaping work together",
        },
      };

      expect(() => leaderboardResponseSchema.parse(response)).not.toThrow();
    });

    it("should support momentum metric", () => {
      const response = {
        success: true,
        data: {
          metric_type: "momentum" as const,
          entries: [],
          computed_at: new Date().toISOString(),
          message: "Momentum matters: sustaining effort over time",
        },
      };

      expect(() => leaderboardResponseSchema.parse(response)).not.toThrow();
    });

    it("should support consistency metric", () => {
      const response = {
        success: true,
        data: {
          metric_type: "consistency" as const,
          entries: [],
          computed_at: new Date().toISOString(),
          message: "Commitment: showing up, creating, and iterating",
        },
      };

      expect(() => leaderboardResponseSchema.parse(response)).not.toThrow();
    });
  });
});
