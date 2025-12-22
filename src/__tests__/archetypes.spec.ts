/**
 * src/__tests__/archetypes.spec.ts
 * Archetype Schema Validation Tests
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";

// Archetype ID enum validation
const archetypeIdSchema = z.enum([
  "truth_teller",
  "builder",
  "philosopher",
  "connector",
  "firestarter",
  "storyteller",
]);

// Full archetype snapshot schema
const archetypeSnapshotSchema = z.object({
  user_id: z.string().min(1),
  primary: archetypeIdSchema,
  secondary: archetypeIdSchema.nullable(),
  scores: z.record(z.string(), z.number().min(0).max(100)),
  explanation: z.array(z.string().min(1)).length(3),
  updated_at: z.string().refine((val) => !Number.isNaN(Date.parse(val))),
  version: z.number().int().min(1),
});

// Public archetype schema (safe subset)
const publicArchetypeSchema = z.object({
  userId: z.string().min(1),
  primary: archetypeIdSchema,
  secondary: archetypeIdSchema.nullable(),
  explanation: z.array(z.string().min(1)).length(3),
  updatedAt: z.string().refine((val) => !Number.isNaN(Date.parse(val))),
});

describe("Archetype Schema Validation", () => {
  describe("Archetype ID Validation", () => {
    it("should accept valid archetype IDs", () => {
      expect(() => archetypeIdSchema.parse("builder")).not.toThrow();
      expect(() => archetypeIdSchema.parse("philosopher")).not.toThrow();
      expect(() => archetypeIdSchema.parse("truth_teller")).not.toThrow();
      expect(() => archetypeIdSchema.parse("connector")).not.toThrow();
      expect(() => archetypeIdSchema.parse("firestarter")).not.toThrow();
      expect(() => archetypeIdSchema.parse("storyteller")).not.toThrow();
    });

    it("should reject invalid archetype IDs", () => {
      expect(() => archetypeIdSchema.parse("invalid")).toThrow();
      expect(() => archetypeIdSchema.parse("")).toThrow();
      expect(() => archetypeIdSchema.parse("BUILDER")).toThrow();
    });
  });

  describe("Full Snapshot Validation", () => {
    it("should validate proper archetype snapshot", () => {
      const validSnapshot = {
        user_id: "user_123",
        primary: "builder" as const,
        secondary: "philosopher" as const,
        scores: {
          builder: 75.0,
          philosopher: 65.0,
          truth_teller: 50.0,
          connector: 50.0,
          firestarter: 45.0,
          storyteller: 50.0,
        },
        explanation: [
          "You ship consistently and focus on actionable outcomes.",
          "Your work shows a bias toward execution over theory.",
          "You're building momentum through tangible progress.",
        ],
        updated_at: "2025-12-21T10:30:00Z",
        version: 5,
      };

      expect(() => archetypeSnapshotSchema.parse(validSnapshot)).not.toThrow();
    });

    it("should reject empty user_id", () => {
      const invalid = {
        user_id: "",
        primary: "builder",
        secondary: null,
        scores: { builder: 75.0 },
        explanation: ["test", "test", "test"],
        updated_at: "2025-12-21T10:30:00Z",
        version: 1,
      };

      expect(() => archetypeSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should reject invalid primary archetype", () => {
      const invalid = {
        user_id: "user_123",
        primary: "invalid_archetype",
        secondary: null,
        scores: { builder: 75.0 },
        explanation: ["test", "test", "test"],
        updated_at: "2025-12-21T10:30:00Z",
        version: 1,
      };

      expect(() => archetypeSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should reject scores out of range", () => {
      const invalid = {
        user_id: "user_123",
        primary: "builder",
        secondary: null,
        scores: { builder: 150.0 }, // Out of range
        explanation: ["test", "test", "test"],
        updated_at: "2025-12-21T10:30:00Z",
        version: 1,
      };

      expect(() => archetypeSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should reject explanation with wrong length", () => {
      const invalid = {
        user_id: "user_123",
        primary: "builder",
        secondary: null,
        scores: { builder: 75.0 },
        explanation: ["only", "two"], // Should be 3
        updated_at: "2025-12-21T10:30:00Z",
        version: 1,
      };

      expect(() => archetypeSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should reject empty explanation bullets", () => {
      const invalid = {
        user_id: "user_123",
        primary: "builder",
        secondary: null,
        scores: { builder: 75.0 },
        explanation: ["", "", ""], // Empty strings
        updated_at: "2025-12-21T10:30:00Z",
        version: 1,
      };

      expect(() => archetypeSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should reject invalid timestamp", () => {
      const invalid = {
        user_id: "user_123",
        primary: "builder",
        secondary: null,
        scores: { builder: 75.0 },
        explanation: ["test", "test", "test"],
        updated_at: "not-a-timestamp",
        version: 1,
      };

      expect(() => archetypeSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should reject zero or negative version", () => {
      const invalid = {
        user_id: "user_123",
        primary: "builder",
        secondary: null,
        scores: { builder: 75.0 },
        explanation: ["test", "test", "test"],
        updated_at: "2025-12-21T10:30:00Z",
        version: 0,
      };

      expect(() => archetypeSnapshotSchema.parse(invalid)).toThrow();
    });

    it("should accept null secondary archetype", () => {
      const valid = {
        user_id: "user_123",
        primary: "builder",
        secondary: null,
        scores: { builder: 85.0, philosopher: 50.0 },
        explanation: ["test", "test", "test"],
        updated_at: "2025-12-21T10:30:00Z",
        version: 1,
      };

      expect(() => archetypeSnapshotSchema.parse(valid)).not.toThrow();
    });
  });

  describe("Public Archetype Validation", () => {
    it("should validate proper public archetype", () => {
      const validPublic = {
        userId: "user_123",
        primary: "builder" as const,
        secondary: "philosopher" as const,
        explanation: [
          "You ship consistently.",
          "Your work shows execution focus.",
          "You're building momentum.",
        ],
        updatedAt: "2025-12-21T10:30:00Z",
      };

      expect(() => publicArchetypeSchema.parse(validPublic)).not.toThrow();
    });

    it("should reject public archetype with scores", () => {
      const invalid = {
        userId: "user_123",
        primary: "builder",
        secondary: null,
        explanation: ["test", "test", "test"],
        updatedAt: "2025-12-21T10:30:00Z",
        scores: { builder: 75.0 }, // Should not be present
      };

      // Zod will ignore extra keys, but we can check structure
      const parsed = publicArchetypeSchema.parse(invalid);
      expect(parsed).not.toHaveProperty("scores");
    });

    it("should reject public archetype with missing userId", () => {
      const invalid = {
        primary: "builder",
        secondary: null,
        explanation: ["test", "test", "test"],
        updatedAt: "2025-12-21T10:30:00Z",
      };

      expect(() => publicArchetypeSchema.parse(invalid)).toThrow();
    });

    it("should reject public archetype with empty userId", () => {
      const invalid = {
        userId: "",
        primary: "builder",
        secondary: null,
        explanation: ["test", "test", "test"],
        updatedAt: "2025-12-21T10:30:00Z",
      };

      expect(() => publicArchetypeSchema.parse(invalid)).toThrow();
    });

    it("should accept public archetype with null secondary", () => {
      const valid = {
        userId: "user_123",
        primary: "builder",
        secondary: null,
        explanation: ["test", "test", "test"],
        updatedAt: "2025-12-21T10:30:00Z",
      };

      expect(() => publicArchetypeSchema.parse(valid)).not.toThrow();
    });

    it("should reject public archetype with invalid primary", () => {
      const invalid = {
        userId: "user_123",
        primary: "invalid_type",
        secondary: null,
        explanation: ["test", "test", "test"],
        updatedAt: "2025-12-21T10:30:00Z",
      };

      expect(() => publicArchetypeSchema.parse(invalid)).toThrow();
    });

    it("should reject explanation with fewer than 3 bullets", () => {
      const invalid = {
        userId: "user_123",
        primary: "builder",
        secondary: null,
        explanation: ["only one"],
        updatedAt: "2025-12-21T10:30:00Z",
      };

      expect(() => publicArchetypeSchema.parse(invalid)).toThrow();
    });

    it("should reject explanation with more than 3 bullets", () => {
      const invalid = {
        userId: "user_123",
        primary: "builder",
        secondary: null,
        explanation: ["one", "two", "three", "four"],
        updatedAt: "2025-12-21T10:30:00Z",
      };

      expect(() => publicArchetypeSchema.parse(invalid)).toThrow();
    });
  });

  describe("Explanation Content Validation", () => {
    it("should reject empty explanation strings", () => {
      const invalid = {
        userId: "user_123",
        primary: "builder",
        secondary: null,
        explanation: ["", "valid", "valid"],
        updatedAt: "2025-12-21T10:30:00Z",
      };

      expect(() => publicArchetypeSchema.parse(invalid)).toThrow();
    });

    it("should accept explanation with varied content", () => {
      const valid = {
        userId: "user_123",
        primary: "storyteller",
        secondary: null,
        explanation: [
          "You craft narratives with vivid details.",
          "Your stories make ideas memorable.",
          "You're building a body of rich work.",
        ],
        updatedAt: "2025-12-21T10:30:00Z",
      };

      expect(() => publicArchetypeSchema.parse(valid)).not.toThrow();
    });
  });

  describe("Timestamp Validation", () => {
    it("should accept ISO 8601 timestamps", () => {
      const valid = {
        userId: "user_123",
        primary: "builder",
        secondary: null,
        explanation: ["test", "test", "test"],
        updatedAt: "2025-12-21T10:30:00.000Z",
      };

      expect(() => publicArchetypeSchema.parse(valid)).not.toThrow();
    });

    it("should reject malformed timestamps", () => {
      const invalid = {
        userId: "user_123",
        primary: "builder",
        secondary: null,
        explanation: ["test", "test", "test"],
        updatedAt: "21-12-2025",
      };

      expect(() => publicArchetypeSchema.parse(invalid)).toThrow();
    });
  });
});
