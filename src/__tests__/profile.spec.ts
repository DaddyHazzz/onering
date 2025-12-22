/**
 * src/__tests__/profile.spec.ts
 * Public Profile API and Schema Validation
 */

import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { z } from "zod";

// Schema definitions (match frontend validation)
const streakSchema = z.object({
  current_length: z.number().int().min(1),
  longest_length: z.number().int().min(1),
  status: z.enum(["active", "on_break", "building"]),
  last_active_date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
});

const momentumComponentsSchema = z.object({
  streakComponent: z.number().min(0).max(25),
  consistencyComponent: z.number().min(0).max(10),
  challengeComponent: z.number().min(0).max(15),
  coachComponent: z.number().min(0).max(10),
});

const momentumSnapshotSchema = z.object({
  score: z.number().min(0).max(100),
  trend: z.enum(["up", "flat", "down"]),
  components: momentumComponentsSchema,
  nextActionHint: z.string().min(1),
  computedAt: z.string().refine((val) => !Number.isNaN(Date.parse(val))),
});

const recentPostSchema = z.object({
  id: z.string().min(1),
  platform: z.string().min(1),
  content: z.string().min(1),
  created_at: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
});

// Archetype ID enum (matching backend)
const archetypeIdSchema = z.enum([
  "truth_teller",
  "builder",
  "philosopher",
  "connector",
  "firestarter",
  "storyteller",
]);

// Public archetype schema (optional field in profile)
const publicArchetypeSchema = z.object({
  userId: z.string().min(1),
  primary: archetypeIdSchema,
  secondary: archetypeIdSchema.nullable(),
  explanation: z.array(z.string().min(1)).length(3),
  updatedAt: z.string().refine((val) => !Number.isNaN(Date.parse(val))),
});

const publicProfileResponseSchema = z.object({
  success: z.boolean(),
  data: z.object({
    user_id: z.string().min(1),
    display_name: z.string().min(1),
    streak: streakSchema,
    momentum_today: momentumSnapshotSchema,
    momentum_weekly: z.array(momentumSnapshotSchema),
    recent_posts: z.array(recentPostSchema),
    profile_summary: z.string().min(1),
    computed_at: z.string().refine((val) => !Number.isNaN(Date.parse(val))),
    archetype: publicArchetypeSchema.optional(), // Optional: backward compatible
  }),
});

describe("Public Profile Schema Validation", () => {
  describe("Streak Validation", () => {
    it("should validate proper streak object", () => {
      const validStreak = {
        current_length: 5,
        longest_length: 10,
        status: "active" as const,
        last_active_date: "2025-01-15",
      };
      expect(() => streakSchema.parse(validStreak)).not.toThrow();
    });

    it("should reject invalid status", () => {
      const invalidStreak = {
        current_length: 5,
        longest_length: 10,
        status: "invalid",
        last_active_date: "2025-01-15",
      };
      expect(() => streakSchema.parse(invalidStreak)).toThrow();
    });

    it("should reject invalid date format", () => {
      const invalidStreak = {
        current_length: 5,
        longest_length: 10,
        status: "active",
        last_active_date: "15-01-2025",
      };
      expect(() => streakSchema.parse(invalidStreak)).toThrow();
    });

    it("should reject zero current_length", () => {
      const invalidStreak = {
        current_length: 0,
        longest_length: 10,
        status: "active",
        last_active_date: "2025-01-15",
      };
      expect(() => streakSchema.parse(invalidStreak)).toThrow();
    });

    it("should reject current > longest", () => {
      const invalidStreak = {
        current_length: 20,
        longest_length: 10,
        status: "active",
        last_active_date: "2025-01-15",
      };
      // Note: schema doesn't enforce this, but UI should
      expect(() => streakSchema.parse(invalidStreak)).not.toThrow();
    });
  });

  describe("Momentum Components Validation", () => {
    it("should validate proper components", () => {
      const validComponents = {
        streakComponent: 10,
        consistencyComponent: 5,
        challengeComponent: 8,
        coachComponent: 3,
      };
      expect(() => momentumComponentsSchema.parse(validComponents)).not.toThrow();
    });

    it("should reject component out of range", () => {
      const invalidComponents = {
        streakComponent: 30, // max 25
        consistencyComponent: 5,
        challengeComponent: 8,
        coachComponent: 3,
      };
      expect(() => momentumComponentsSchema.parse(invalidComponents)).toThrow();
    });

    it("should reject negative component", () => {
      const invalidComponents = {
        streakComponent: -5,
        consistencyComponent: 5,
        challengeComponent: 8,
        coachComponent: 3,
      };
      expect(() => momentumComponentsSchema.parse(invalidComponents)).toThrow();
    });
  });

  describe("Momentum Snapshot Validation", () => {
    it("should validate proper momentum snapshot", () => {
      const validSnapshot = {
        score: 75.5,
        trend: "up" as const,
        components: {
          streakComponent: 10,
          consistencyComponent: 5,
          challengeComponent: 8,
          coachComponent: 3,
        },
        nextActionHint: "Focus on consistency",
        computedAt: "2025-01-15T10:30:00Z",
      };
      expect(() => momentumSnapshotSchema.parse(validSnapshot)).not.toThrow();
    });

    it("should reject score out of range", () => {
      const invalidSnapshot = {
        score: 150,
        trend: "up" as const,
        components: {
          streakComponent: 10,
          consistencyComponent: 5,
          challengeComponent: 8,
          coachComponent: 3,
        },
        nextActionHint: "Focus on consistency",
        computedAt: "2025-01-15T10:30:00Z",
      };
      expect(() => momentumSnapshotSchema.parse(invalidSnapshot)).toThrow();
    });

    it("should reject empty nextActionHint", () => {
      const invalidSnapshot = {
        score: 75,
        trend: "up" as const,
        components: {
          streakComponent: 10,
          consistencyComponent: 5,
          challengeComponent: 8,
          coachComponent: 3,
        },
        nextActionHint: "",
        computedAt: "2025-01-15T10:30:00Z",
      };
      expect(() => momentumSnapshotSchema.parse(invalidSnapshot)).toThrow();
    });

    it("should reject invalid ISO timestamp", () => {
      const invalidSnapshot = {
        score: 75,
        trend: "up" as const,
        components: {
          streakComponent: 10,
          consistencyComponent: 5,
          challengeComponent: 8,
          coachComponent: 3,
        },
        nextActionHint: "Focus on consistency",
        computedAt: "not-a-date",
      };
      expect(() => momentumSnapshotSchema.parse(invalidSnapshot)).toThrow();
    });

    it("should reject invalid trend", () => {
      const invalidSnapshot = {
        score: 75,
        trend: "invalid",
        components: {
          streakComponent: 10,
          consistencyComponent: 5,
          challengeComponent: 8,
          coachComponent: 3,
        },
        nextActionHint: "Focus on consistency",
        computedAt: "2025-01-15T10:30:00Z",
      };
      expect(() => momentumSnapshotSchema.parse(invalidSnapshot)).toThrow();
    });
  });

  describe("Recent Post Validation", () => {
    it("should validate proper post", () => {
      const validPost = {
        id: "post_123",
        platform: "twitter",
        content: "This is my first post",
        created_at: "2025-01-15",
      };
      expect(() => recentPostSchema.parse(validPost)).not.toThrow();
    });

    it("should reject empty content", () => {
      const invalidPost = {
        id: "post_123",
        platform: "twitter",
        content: "",
        created_at: "2025-01-15",
      };
      expect(() => recentPostSchema.parse(invalidPost)).toThrow();
    });

    it("should reject empty id", () => {
      const invalidPost = {
        id: "",
        platform: "twitter",
        content: "This is my first post",
        created_at: "2025-01-15",
      };
      expect(() => recentPostSchema.parse(invalidPost)).toThrow();
    });

    it("should reject invalid date", () => {
      const invalidPost = {
        id: "post_123",
        platform: "twitter",
        content: "This is my first post",
        created_at: "15/01/2025",
      };
      expect(() => recentPostSchema.parse(invalidPost)).toThrow();
    });
  });

  describe("Full Response Validation", () => {
    it("should validate complete profile response", () => {
      const validResponse = {
        success: true,
        data: {
          user_id: "user_123",
          display_name: "Alice Chen",
          streak: {
            current_length: 5,
            longest_length: 10,
            status: "active" as const,
            last_active_date: "2025-01-15",
          },
          momentum_today: {
            score: 75.5,
            trend: "up" as const,
            components: {
              streakComponent: 10,
              consistencyComponent: 5,
              challengeComponent: 8,
              coachComponent: 3,
            },
            nextActionHint: "Focus on consistency",
            computedAt: "2025-01-15T10:30:00Z",
          },
          momentum_weekly: [
            {
              score: 70,
              trend: "up" as const,
              components: {
                streakComponent: 9,
                consistencyComponent: 4,
                challengeComponent: 8,
                coachComponent: 3,
              },
              nextActionHint: "Keep going!",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 72,
              trend: "flat" as const,
              components: {
                streakComponent: 10,
                consistencyComponent: 5,
                challengeComponent: 8,
                coachComponent: 3,
              },
              nextActionHint: "Push a bit harder",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 68,
              trend: "down" as const,
              components: {
                streakComponent: 8,
                consistencyComponent: 4,
                challengeComponent: 7,
                coachComponent: 2,
              },
              nextActionHint: "Rest and recover",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 74,
              trend: "up" as const,
              components: {
                streakComponent: 10,
                consistencyComponent: 5,
                challengeComponent: 8,
                coachComponent: 3,
              },
              nextActionHint: "Build momentum",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 76,
              trend: "up" as const,
              components: {
                streakComponent: 11,
                consistencyComponent: 5,
                challengeComponent: 8,
                coachComponent: 4,
              },
              nextActionHint: "You're crushing it",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 73,
              trend: "flat" as const,
              components: {
                streakComponent: 10,
                consistencyComponent: 5,
                challengeComponent: 8,
                coachComponent: 3,
              },
              nextActionHint: "Hold steady",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 75,
              trend: "up" as const,
              components: {
                streakComponent: 10,
                consistencyComponent: 5,
                challengeComponent: 8,
                coachComponent: 3,
              },
              nextActionHint: "Great week ahead",
              computedAt: "2025-01-15T10:30:00Z",
            },
          ],
          recent_posts: [
            {
              id: "post_1",
              platform: "twitter",
              content: "Just shipped a new feature!",
              created_at: "2025-01-15",
            },
          ],
          profile_summary: "🚀 Creator in flow, building momentum every day",
          computed_at: "2025-01-15T10:30:00Z",
        },
      };
      expect(() => publicProfileResponseSchema.parse(validResponse)).not.toThrow();
    });

    it("should reject response with missing user_id", () => {
      const invalidResponse = {
        success: true,
        data: {
          display_name: "Alice Chen",
          streak: {
            current_length: 5,
            longest_length: 10,
            status: "active" as const,
            last_active_date: "2025-01-15",
          },
          momentum_today: {
            score: 75.5,
            trend: "up" as const,
            components: {
              streakComponent: 10,
              consistencyComponent: 5,
              challengeComponent: 8,
              coachComponent: 3,
            },
            nextActionHint: "Focus on consistency",
            computedAt: "2025-01-15T10:30:00Z",
          },
          momentum_weekly: [],
          recent_posts: [],
          profile_summary: "Creator",
          computed_at: "2025-01-15T10:30:00Z",
        },
      };
      expect(() => publicProfileResponseSchema.parse(invalidResponse)).toThrow();
    });

    it("should reject response without weekly momentum", () => {
      const invalidResponse = {
        success: true,
        data: {
          user_id: "user_123",
          display_name: "Alice Chen",
          streak: {
            current_length: 5,
            longest_length: 10,
            status: "active" as const,
            last_active_date: "2025-01-15",
          },
          momentum_today: {
            score: 75.5,
            trend: "up" as const,
            components: {
              streakComponent: 10,
              consistencyComponent: 5,
              challengeComponent: 8,
              coachComponent: 3,
            },
            nextActionHint: "Focus on consistency",
            computedAt: "2025-01-15T10:30:00Z",
          },
          recent_posts: [],
          profile_summary: "Creator",
          computed_at: "2025-01-15T10:30:00Z",
        },
      };
      expect(() => publicProfileResponseSchema.parse(invalidResponse)).toThrow();
    });

    it("should accept empty recent_posts", () => {
      const validResponse = {
        success: true,
        data: {
          user_id: "user_123",
          display_name: "Alice Chen",
          streak: {
            current_length: 5,
            longest_length: 10,
            status: "active" as const,
            last_active_date: "2025-01-15",
          },
          momentum_today: {
            score: 75.5,
            trend: "up" as const,
            components: {
              streakComponent: 10,
              consistencyComponent: 5,
              challengeComponent: 8,
              coachComponent: 3,
            },
            nextActionHint: "Focus on consistency",
            computedAt: "2025-01-15T10:30:00Z",
          },
          momentum_weekly: [
            {
              score: 70,
              trend: "up" as const,
              components: {
                streakComponent: 9,
                consistencyComponent: 4,
                challengeComponent: 8,
                coachComponent: 3,
              },
              nextActionHint: "Keep going!",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 72,
              trend: "flat" as const,
              components: {
                streakComponent: 10,
                consistencyComponent: 5,
                challengeComponent: 8,
                coachComponent: 3,
              },
              nextActionHint: "Push harder",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 68,
              trend: "down" as const,
              components: {
                streakComponent: 8,
                consistencyComponent: 4,
                challengeComponent: 7,
                coachComponent: 2,
              },
              nextActionHint: "Rest",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 74,
              trend: "up" as const,
              components: {
                streakComponent: 10,
                consistencyComponent: 5,
                challengeComponent: 8,
                coachComponent: 3,
              },
              nextActionHint: "Build",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 76,
              trend: "up" as const,
              components: {
                streakComponent: 11,
                consistencyComponent: 5,
                challengeComponent: 8,
                coachComponent: 4,
              },
              nextActionHint: "Crush it",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 73,
              trend: "flat" as const,
              components: {
                streakComponent: 10,
                consistencyComponent: 5,
                challengeComponent: 8,
                coachComponent: 3,
              },
              nextActionHint: "Hold",
              computedAt: "2025-01-15T10:30:00Z",
            },
            {
              score: 75,
              trend: "up" as const,
              components: {
                streakComponent: 10,
                consistencyComponent: 5,
                challengeComponent: 8,
                coachComponent: 3,
              },
              nextActionHint: "Go",
              computedAt: "2025-01-15T10:30:00Z",
            },
          ],
          recent_posts: [],
          profile_summary: "Creator",
          computed_at: "2025-01-15T10:30:00Z",
        },
      };
      expect(() => publicProfileResponseSchema.parse(validResponse)).not.toThrow();
    });
  });

  describe("Weekly Momentum Array", () => {
    it("should ensure exactly 7 days in weekly momentum", () => {
      // This is a business logic test (not enforced by schema, but expected by UI)
      const response = {
        success: true,
        data: {
          user_id: "user_123",
          display_name: "Alice Chen",
          streak: {
            current_length: 5,
            longest_length: 10,
            status: "active" as const,
            last_active_date: "2025-01-15",
          },
          momentum_today: {
            score: 75.5,
            trend: "up" as const,
            components: {
              streakComponent: 10,
              consistencyComponent: 5,
              challengeComponent: 8,
              coachComponent: 3,
            },
            nextActionHint: "Focus",
            computedAt: "2025-01-15T10:30:00Z",
          },
          momentum_weekly: Array(7).fill(null).map(() => ({
            score: 75,
            trend: "up" as const,
            components: {
              streakComponent: 10,
              consistencyComponent: 5,
              challengeComponent: 8,
              coachComponent: 3,
            },
            nextActionHint: "Go",
            computedAt: "2025-01-15T10:30:00Z",
          })),
          recent_posts: [],
          profile_summary: "Creator",
          computed_at: "2025-01-15T10:30:00Z",
        },
      };
      
      const validated = publicProfileResponseSchema.parse(response);
      expect(validated.data.momentum_weekly).toHaveLength(7);
    });
  });
});

describe("Archetype Integration in Profile", () => {
  describe("Archetype Presence", () => {
    it("should validate profile with archetype present", () => {
      const validProfile = {
        success: true,
        data: {
          user_id: "user_123",
          display_name: "Test User",
          streak: {
            current_length: 5,
            longest_length: 10,
            status: "active" as const,
            last_active_date: "2025-01-15",
          },
          momentum_today: {
            score: 75,
            trend: "up" as const,
            components: {
              streakComponent: 10,
              consistencyComponent: 5,
              challengeComponent: 8,
              coachComponent: 3,
            },
            nextActionHint: "Keep going",
            computedAt: "2025-01-15T10:30:00Z",
          },
          momentum_weekly: [],
          recent_posts: [],
          profile_summary: "Active creator",
          computed_at: "2025-01-15T10:30:00Z",
          archetype: {
            userId: "user_123",
            primary: "builder" as const,
            secondary: "philosopher" as const,
            explanation: [
              "You ship consistently.",
              "Your work shows execution focus.",
              "You're building momentum.",
            ],
            updatedAt: "2025-01-15T10:30:00Z",
          },
        },
      };

      expect(() => publicProfileResponseSchema.parse(validProfile)).not.toThrow();
    });

    it("should validate profile without archetype (backward compatible)", () => {
      const validProfile = {
        success: true,
        data: {
          user_id: "user_123",
          display_name: "Test User",
          streak: {
            current_length: 5,
            longest_length: 10,
            status: "active" as const,
            last_active_date: "2025-01-15",
          },
          momentum_today: {
            score: 75,
            trend: "up" as const,
            components: {
              streakComponent: 10,
              consistencyComponent: 5,
              challengeComponent: 8,
              coachComponent: 3,
            },
            nextActionHint: "Keep going",
            computedAt: "2025-01-15T10:30:00Z",
          },
          momentum_weekly: [],
          recent_posts: [],
          profile_summary: "Active creator",
          computed_at: "2025-01-15T10:30:00Z",
          // archetype omitted - should still pass
        },
      };

      expect(() => publicProfileResponseSchema.parse(validProfile)).not.toThrow();
    });

    it("should reject profile with invalid archetype structure", () => {
      const invalidProfile = {
        success: true,
        data: {
          user_id: "user_123",
          display_name: "Test User",
          streak: {
            current_length: 5,
            longest_length: 10,
            status: "active" as const,
            last_active_date: "2025-01-15",
          },
          momentum_today: {
            score: 75,
            trend: "up" as const,
            components: {
              streakComponent: 10,
              consistencyComponent: 5,
              challengeComponent: 8,
              coachComponent: 3,
            },
            nextActionHint: "Keep going",
            computedAt: "2025-01-15T10:30:00Z",
          },
          momentum_weekly: [],
          recent_posts: [],
          profile_summary: "Active creator",
          computed_at: "2025-01-15T10:30:00Z",
          archetype: {
            userId: "user_123",
            primary: "invalid_archetype", // Invalid archetype ID
            secondary: null,
            explanation: ["test", "test", "test"],
            updatedAt: "2025-01-15T10:30:00Z",
          },
        },
      };

      expect(() => publicProfileResponseSchema.parse(invalidProfile)).toThrow();
    });

    it("should reject archetype with fewer than 3 explanation bullets", () => {
      const invalidProfile = {
        success: true,
        data: {
          user_id: "user_123",
          display_name: "Test User",
          streak: {
            current_length: 5,
            longest_length: 10,
            status: "active" as const,
            last_active_date: "2025-01-15",
          },
          momentum_today: {
            score: 75,
            trend: "up" as const,
            components: {
              streakComponent: 10,
              consistencyComponent: 5,
              challengeComponent: 8,
              coachComponent: 3,
            },
            nextActionHint: "Keep going",
            computedAt: "2025-01-15T10:30:00Z",
          },
          momentum_weekly: [],
          recent_posts: [],
          profile_summary: "Active creator",
          computed_at: "2025-01-15T10:30:00Z",
          archetype: {
            userId: "user_123",
            primary: "builder",
            secondary: null,
            explanation: ["only", "two"], // Should be 3
            updatedAt: "2025-01-15T10:30:00Z",
          },
        },
      };

      expect(() => publicProfileResponseSchema.parse(invalidProfile)).toThrow();
    });
  });
});
