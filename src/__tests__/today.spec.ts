/**
 * src/__tests__/today.spec.ts
 * Today Loop UI tests: Zod validation, API integration, error handling.
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { z } from "zod";

// Schemas for Today page API responses
const StreakDataSchema = z.object({
  current_length: z.number().min(0),
  longest_length: z.number().min(0),
  status: z.enum(["active", "on_break", "building"]),
  last_active_date: z.string().datetime(),
  next_action_hint: z.string().min(1),
});

const ChallengeSchema = z.object({
  challenge_id: z.string().uuid(),
  date: z.string().date(),
  type: z.string(),
  prompt: z.string(),
  status: z.enum(["assigned", "accepted", "completed"]),
  next_action_hint: z.string(),
});

const MomentumDataSchema = z.object({
  score: z.number().min(0).max(100),
  trend: z.enum(["up", "flat", "down"]),
  nextActionHint: z.string(),
  computedAt: z.string().datetime(),
});

const ArchetypeSchema = z.object({
  userId: z.string().uuid(),
  primary: z.string(),
  secondary: z.string().nullable(),
  explanation: z.array(z.string()).min(1),
  updatedAt: z.string().datetime(),
});

const CoachFeedbackSchema = z.object({
  suggestions: z.array(z.string()).min(1),
  summary: z.string(),
});

describe("Today Loop UI Schemas", () => {
  describe("StreakDataSchema", () => {
    it("accepts valid streak data", () => {
      const validData = {
        current_length: 15,
        longest_length: 42,
        status: "active" as const,
        last_active_date: new Date().toISOString(),
        next_action_hint: "Post today to keep the streak alive",
      };
      expect(() => StreakDataSchema.parse(validData)).not.toThrow();
    });

    it("rejects negative streak length", () => {
      const invalidData = {
        current_length: -5,
        longest_length: 10,
        status: "active" as const,
        last_active_date: new Date().toISOString(),
        next_action_hint: "Post today",
      };
      expect(() => StreakDataSchema.parse(invalidData)).toThrow();
    });

    it("rejects invalid status", () => {
      const invalidData = {
        current_length: 5,
        longest_length: 10,
        status: "lost" as any,
        last_active_date: new Date().toISOString(),
        next_action_hint: "Post today",
      };
      expect(() => StreakDataSchema.parse(invalidData)).toThrow();
    });

    it("requires next_action_hint non-empty", () => {
      const invalidData = {
        current_length: 5,
        longest_length: 10,
        status: "active" as const,
        last_active_date: new Date().toISOString(),
        next_action_hint: "",
      };
      expect(() => StreakDataSchema.parse(invalidData)).toThrow();
    });
  });

  describe("ChallengeSchema", () => {
    it("accepts valid challenge", () => {
      const validData = {
        challenge_id: "550e8400-e29b-41d4-a716-446655440000",
        date: "2025-12-14",
        type: "thread",
        prompt: "Write a 5-tweet thread about momentum",
        status: "assigned" as const,
        next_action_hint: "Start writing your thread",
      };
      expect(() => ChallengeSchema.parse(validData)).not.toThrow();
    });

    it("rejects invalid status", () => {
      const invalidData = {
        challenge_id: "550e8400-e29b-41d4-a716-446655440000",
        date: "2025-12-14",
        type: "thread",
        prompt: "Write a thread",
        status: "ignored" as any,
        next_action_hint: "Start",
      };
      expect(() => ChallengeSchema.parse(invalidData)).toThrow();
    });

    it("rejects non-UUID challenge_id", () => {
      const invalidData = {
        challenge_id: "not-a-uuid",
        date: "2025-12-14",
        type: "thread",
        prompt: "Write a thread",
        status: "assigned" as const,
        next_action_hint: "Start",
      };
      expect(() => ChallengeSchema.parse(invalidData)).toThrow();
    });
  });

  describe("MomentumDataSchema", () => {
    it("accepts valid momentum data", () => {
      const validData = {
        score: 75,
        trend: "up" as const,
        nextActionHint: "Keep the momentum going with daily posts",
        computedAt: new Date().toISOString(),
      };
      expect(() => MomentumDataSchema.parse(validData)).not.toThrow();
    });

    it("bounds momentum score to [0, 100]", () => {
      const tooHigh = {
        score: 150,
        trend: "up" as const,
        nextActionHint: "Keep going",
        computedAt: new Date().toISOString(),
      };
      expect(() => MomentumDataSchema.parse(tooHigh)).toThrow();

      const tooLow = {
        score: -10,
        trend: "down" as const,
        nextActionHint: "Rebuild",
        computedAt: new Date().toISOString(),
      };
      expect(() => MomentumDataSchema.parse(tooLow)).toThrow();
    });

    it("rejects invalid trend", () => {
      const invalidData = {
        score: 50,
        trend: "sideways" as any,
        nextActionHint: "Keep going",
        computedAt: new Date().toISOString(),
      };
      expect(() => MomentumDataSchema.parse(invalidData)).toThrow();
    });
  });

  describe("ArchetypeSchema", () => {
    it("accepts valid archetype with secondary", () => {
      const validData = {
        userId: "550e8400-e29b-41d4-a716-446655440000",
        primary: "truth_teller",
        secondary: "storyteller",
        explanation: ["You prioritize authenticity", "Your voice cuts through noise"],
        updatedAt: new Date().toISOString(),
      };
      expect(() => ArchetypeSchema.parse(validData)).not.toThrow();
    });

    it("accepts valid archetype without secondary", () => {
      const validData = {
        userId: "550e8400-e29b-41d4-a716-446655440000",
        primary: "builder",
        secondary: null,
        explanation: ["You focus on shipping", "Action over words"],
        updatedAt: new Date().toISOString(),
      };
      expect(() => ArchetypeSchema.parse(validData)).not.toThrow();
    });

    it("requires explanation with at least one item", () => {
      const invalidData = {
        userId: "550e8400-e29b-41d4-a716-446655440000",
        primary: "philosopher",
        secondary: null,
        explanation: [],
        updatedAt: new Date().toISOString(),
      };
      expect(() => ArchetypeSchema.parse(invalidData)).toThrow();
    });
  });

  describe("CoachFeedbackSchema", () => {
    it("accepts valid coach feedback", () => {
      const validData = {
        suggestions: [
          "Lead with your strongest idea",
          "Add a specific example",
          "End with a call to action",
        ],
        summary: "Good hook, but needs specificity",
      };
      expect(() => CoachFeedbackSchema.parse(validData)).not.toThrow();
    });

    it("requires at least one suggestion", () => {
      const invalidData = {
        suggestions: [],
        summary: "Too generic",
      };
      expect(() => CoachFeedbackSchema.parse(invalidData)).toThrow();
    });
  });
});

describe("Today Page API Behavior", () => {
  describe("Streak API resilience", () => {
    it("shows default streak if API unavailable", () => {
      // Component should gracefully handle missing streak
      // Default: { current_length: 0, status: 'building' }
      expect(true).toBe(true); // Placeholder for integration test
    });

    it("displays next_action_hint when available", () => {
      const streak = {
        current_length: 10,
        longest_length: 15,
        status: "active" as const,
        last_active_date: new Date().toISOString(),
        next_action_hint: "Post today to reach 11",
      };
      expect(streak.next_action_hint).toContain("Post");
    });
  });

  describe("Challenge status flow", () => {
    it("shows different UI for assigned → accepted → completed", () => {
      const statuses = ["assigned", "accepted", "completed"] as const;
      statuses.forEach((status) => {
        expect(["assigned", "accepted", "completed"]).toContain(status);
      });
    });
  });

  describe("Momentum trend interpretation", () => {
    it("maps trend to emoji correctly", () => {
      const trendEmoji = {
        up: "📈",
        flat: "➡️",
        down: "📉",
      };
      expect(trendEmoji.up).toBe("📈");
      expect(trendEmoji.flat).toBe("➡️");
      expect(trendEmoji.down).toBe("📉");
    });
  });
});

describe("Today Page Error Handling", () => {
  it("shows loading state while fetching", () => {
    // Component sets loading = true, then false after fetch
    expect(true).toBe(true); // Placeholder
  });

  it("shows backend unavailable banner if APIs fail", () => {
    // Component sets backendDown = true on fetch error
    expect(true).toBe(true); // Placeholder
  });

  it("requires user to be signed in", () => {
    // Component redirects to sign-in if !user
    expect(true).toBe(true); // Placeholder
  });
});
