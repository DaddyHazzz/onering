import { describe, it, expect } from "vitest";
import { z } from "zod";

// Replicate the schemas from the API
const momentumComponentsSchema = z.object({
  streakComponent: z.number().min(0).max(25),
  consistencyComponent: z.number().min(0).max(10),
  challengeComponent: z.number().min(0).max(15),
  coachComponent: z.number().min(0).max(10),
});

const momentumSnapshotSchema = z.object({
  userId: z.string().min(1, "userId must not be empty"),
  date: z
    .string()
    .regex(
      /^\d{4}-\d{2}-\d{2}$/,
      "date must be in YYYY-MM-DD format"
    ),
  score: z.number().min(0).max(100),
  trend: z.enum(["up", "flat", "down"]),
  components: momentumComponentsSchema,
  nextActionHint: z.string().min(1, "nextActionHint must not be empty"),
  computedAt: z
    .string()
    .refine((val) => !Number.isNaN(Date.parse(val)), "computedAt must be a valid ISO timestamp"),
});

describe("Momentum Frontend Schemas", () => {
  describe("momentumComponentsSchema", () => {
    it("should validate valid components", () => {
      const valid = {
        streakComponent: 20.0,
        consistencyComponent: 8.0,
        challengeComponent: 15.0,
        coachComponent: 5.0,
      };
      expect(() => momentumComponentsSchema.parse(valid)).not.toThrow();
    });

    it("should reject negative component", () => {
      const invalid = {
        streakComponent: -1.0,
        consistencyComponent: 8.0,
        challengeComponent: 15.0,
        coachComponent: 5.0,
      };
      expect(() => momentumComponentsSchema.parse(invalid)).toThrow();
    });

    it("should reject component over max", () => {
      const invalid = {
        streakComponent: 26.0, // max is 25
        consistencyComponent: 8.0,
        challengeComponent: 15.0,
        coachComponent: 5.0,
      };
      expect(() => momentumComponentsSchema.parse(invalid)).toThrow();
    });

    it("should accept component at max boundary", () => {
      const valid = {
        streakComponent: 25.0,
        consistencyComponent: 10.0,
        challengeComponent: 15.0,
        coachComponent: 10.0,
      };
      expect(() => momentumComponentsSchema.parse(valid)).not.toThrow();
    });
  });

  describe("momentumSnapshotSchema", () => {
    const validSnapshot = {
      userId: "user_123",
      date: "2025-12-21",
      score: 75.5,
      trend: "up" as const,
      components: {
        streakComponent: 20.0,
        consistencyComponent: 8.0,
        challengeComponent: 15.0,
        coachComponent: 5.0,
      },
      nextActionHint: "You're in flow. Keep riding this wave today.",
      computedAt: "2025-12-21T14:30:00+00:00",
    };

    it("should validate a valid snapshot", () => {
      expect(() => momentumSnapshotSchema.parse(validSnapshot)).not.toThrow();
    });

    it("should require userId", () => {
      const invalid = { ...validSnapshot, userId: "" };
      expect(() => momentumSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should require date in correct format", () => {
      const invalid = { ...validSnapshot, date: "invalid-date" };
      expect(() => momentumSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should clamp score to 0-100", () => {
      const tooHigh = { ...validSnapshot, score: 101.0 };
      expect(() => momentumSnapshotSchema.parse(tooHigh)).toThrow();

      const tooLow = { ...validSnapshot, score: -0.1 };
      expect(() => momentumSnapshotSchema.parse(tooLow)).toThrow();
    });

    it("should validate trend enum", () => {
      const validTrends = ["up", "flat", "down"];
      for (const trend of validTrends) {
        const snapshot = { ...validSnapshot, trend: trend as any };
        expect(() => momentumSnapshotSchema.parse(snapshot)).not.toThrow();
      }
    });

    it("should reject invalid trend", () => {
      const invalid = { ...validSnapshot, trend: "rising" as any };
      expect(() => momentumSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should require non-empty nextActionHint", () => {
      const invalid = { ...validSnapshot, nextActionHint: "" };
      expect(() => momentumSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should validate computedAt as ISO string", () => {
      const valid = { ...validSnapshot, computedAt: "2025-12-21T14:30:00Z" };
      expect(() => momentumSnapshotSchema.parse(valid)).not.toThrow();
    });

    it("should reject invalid ISO timestamp", () => {
      const invalid = { ...validSnapshot, computedAt: "not-a-timestamp" };
      expect(() => momentumSnapshotSchema.parse(invalid)).toThrow();
    });
  });

  describe("momentumSnapshotArray", () => {
    const validSnapshot = {
      userId: "user_123",
      date: "2025-12-21",
      score: 75.5,
      trend: "up" as const,
      components: {
        streakComponent: 20.0,
        consistencyComponent: 8.0,
        challengeComponent: 15.0,
        coachComponent: 5.0,
      },
      nextActionHint: "Action hint",
      computedAt: "2025-12-21T14:30:00+00:00",
    };

    it("should validate array of snapshots", () => {
      const snapshots = [validSnapshot, validSnapshot];
      const schema = z.array(momentumSnapshotSchema);
      expect(() => schema.parse(snapshots)).not.toThrow();
    });

    it("should reject array with invalid snapshot", () => {
      const invalid = [validSnapshot, { ...validSnapshot, score: 101.0 }];
      const schema = z.array(momentumSnapshotSchema);
      expect(() => schema.parse(invalid)).toThrow();
    });
  });
});
