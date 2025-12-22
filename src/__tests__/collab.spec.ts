/**
 * src/__tests__/collab.spec.ts
 * Collaboration API schema validation and response shape tests
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";

// Schema definitions (mirrors backend Pydantic)
const DraftStatusSchema = z.enum(["active", "locked", "completed"]);

const DraftSegmentSchema = z.object({
  segment_id: z.string().uuid(),
  draft_id: z.string().uuid(),
  user_id: z.string(),
  content: z.string().max(500),
  created_at: z.string().datetime(),
  segment_order: z.number().nonnegative(),
  idempotency_key: z.string().uuid(),
});

const RingStateSchema = z.object({
  draft_id: z.string().uuid(),
  current_holder_id: z.string(),
  holders_history: z.array(z.string()).min(1),
  passed_at: z.string().datetime().nullable(),
  idempotency_key: z.string().uuid().nullable(),
});

const CollabDraftSchema = z.object({
  draft_id: z.string().uuid(),
  creator_id: z.string(),
  title: z.string().max(200),
  platform: z.enum(["x", "instagram", "tiktok", "youtube"]),
  status: DraftStatusSchema,
  segments: z.array(DraftSegmentSchema),
  ring_state: RingStateSchema,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  target_publish_at: z.string().datetime().nullable(),
});

const CreateDraftRequestSchema = z.object({
  title: z.string().min(1).max(200),
  platform: z.enum(["x", "instagram", "tiktok", "youtube"]),
  initial_segment: z.string().max(500).optional(),
});

const SegmentAppendRequestSchema = z.object({
  content: z.string().min(1).max(500),
  idempotency_key: z.string().uuid(),
});

const PassRingRequestSchema = z.object({
  to_user_id: z.string(),
  idempotency_key: z.string().uuid(),
});

describe("Collaboration Schemas", () => {
  describe("DraftStatus", () => {
    it("accepts valid statuses", () => {
      expect(DraftStatusSchema.parse("active")).toBe("active");
      expect(DraftStatusSchema.parse("locked")).toBe("locked");
      expect(DraftStatusSchema.parse("completed")).toBe("completed");
    });

    it("rejects invalid status", () => {
      expect(() => DraftStatusSchema.parse("pending")).toThrow();
    });
  });

  describe("DraftSegment", () => {
    it("accepts valid segment", () => {
      const segment = {
        segment_id: "123e4567-e89b-12d3-a456-426614174000",
        draft_id: "223e4567-e89b-12d3-a456-426614174000",
        user_id: "user123",
        content: "Hello world",
        created_at: "2025-12-21T10:00:00Z",
        segment_order: 0,
        idempotency_key: "323e4567-e89b-12d3-a456-426614174000",
      };
      expect(DraftSegmentSchema.parse(segment)).toEqual(segment);
    });

    it("rejects segment with invalid content length", () => {
      const segment = {
        segment_id: "123e4567-e89b-12d3-a456-426614174000",
        draft_id: "223e4567-e89b-12d3-a456-426614174000",
        user_id: "user123",
        content: "x".repeat(501),
        created_at: "2025-12-21T10:00:00Z",
        segment_order: 0,
        idempotency_key: "323e4567-e89b-12d3-a456-426614174000",
      };
      expect(() => DraftSegmentSchema.parse(segment)).toThrow();
    });

    it("rejects segment with negative order", () => {
      const segment = {
        segment_id: "123e4567-e89b-12d3-a456-426614174000",
        draft_id: "223e4567-e89b-12d3-a456-426614174000",
        user_id: "user123",
        content: "Hello",
        created_at: "2025-12-21T10:00:00Z",
        segment_order: -1,
        idempotency_key: "323e4567-e89b-12d3-a456-426614174000",
      };
      expect(() => DraftSegmentSchema.parse(segment)).toThrow();
    });
  });

  describe("RingState", () => {
    it("accepts valid ring state", () => {
      const ringState = {
        draft_id: "123e4567-e89b-12d3-a456-426614174000",
        current_holder_id: "user123",
        holders_history: ["user123", "user456"],
        passed_at: "2025-12-21T10:05:00Z",
        idempotency_key: "323e4567-e89b-12d3-a456-426614174000",
      };
      expect(RingStateSchema.parse(ringState)).toEqual(ringState);
    });

    it("allows null passed_at and idempotency_key", () => {
      const ringState = {
        draft_id: "123e4567-e89b-12d3-a456-426614174000",
        current_holder_id: "user123",
        holders_history: ["user123"],
        passed_at: null,
        idempotency_key: null,
      };
      expect(RingStateSchema.parse(ringState)).toEqual(ringState);
    });

    it("rejects empty holders_history", () => {
      const ringState = {
        draft_id: "123e4567-e89b-12d3-a456-426614174000",
        current_holder_id: "user123",
        holders_history: [],
        passed_at: null,
        idempotency_key: null,
      };
      expect(() => RingStateSchema.parse(ringState)).toThrow();
    });
  });

  describe("CollabDraft", () => {
    it("accepts valid draft", () => {
      const draft = {
        draft_id: "123e4567-e89b-12d3-a456-426614174000",
        creator_id: "user123",
        title: "My Draft",
        platform: "x" as const,
        status: "active" as const,
        segments: [
          {
            segment_id: "223e4567-e89b-12d3-a456-426614174000",
            draft_id: "123e4567-e89b-12d3-a456-426614174000",
            user_id: "user123",
            content: "Hello",
            created_at: "2025-12-21T10:00:00Z",
            segment_order: 0,
            idempotency_key: "323e4567-e89b-12d3-a456-426614174000",
          },
        ],
        ring_state: {
          draft_id: "123e4567-e89b-12d3-a456-426614174000",
          current_holder_id: "user123",
          holders_history: ["user123"],
          passed_at: null,
          idempotency_key: null,
        },
        created_at: "2025-12-21T10:00:00Z",
        updated_at: "2025-12-21T10:00:00Z",
        target_publish_at: null,
      };
      expect(CollabDraftSchema.parse(draft)).toEqual(draft);
    });

    it("rejects draft with title > 200 chars", () => {
      const draft = {
        draft_id: "123e4567-e89b-12d3-a456-426614174000",
        creator_id: "user123",
        title: "x".repeat(201),
        platform: "x" as const,
        status: "active" as const,
        segments: [],
        ring_state: {
          draft_id: "123e4567-e89b-12d3-a456-426614174000",
          current_holder_id: "user123",
          holders_history: ["user123"],
          passed_at: null,
          idempotency_key: null,
        },
        created_at: "2025-12-21T10:00:00Z",
        updated_at: "2025-12-21T10:00:00Z",
        target_publish_at: null,
      };
      expect(() => CollabDraftSchema.parse(draft)).toThrow();
    });

    it("rejects draft with invalid platform", () => {
      const draft = {
        draft_id: "123e4567-e89b-12d3-a456-426614174000",
        creator_id: "user123",
        title: "My Draft",
        platform: "tiktok_live" as any,
        status: "active" as const,
        segments: [],
        ring_state: {
          draft_id: "123e4567-e89b-12d3-a456-426614174000",
          current_holder_id: "user123",
          holders_history: ["user123"],
          passed_at: null,
          idempotency_key: null,
        },
        created_at: "2025-12-21T10:00:00Z",
        updated_at: "2025-12-21T10:00:00Z",
        target_publish_at: null,
      };
      expect(() => CollabDraftSchema.parse(draft)).toThrow();
    });
  });

  describe("CreateDraftRequest", () => {
    it("accepts valid request", () => {
      const request = {
        title: "New Draft",
        platform: "x" as const,
        initial_segment: "First post",
      };
      expect(CreateDraftRequestSchema.parse(request)).toEqual(request);
    });

    it("accepts request without initial_segment", () => {
      const request = {
        title: "New Draft",
        platform: "instagram" as const,
      };
      expect(CreateDraftRequestSchema.parse(request)).toEqual(request);
    });

    it("rejects empty title", () => {
      const request = {
        title: "",
        platform: "x" as const,
      };
      expect(() => CreateDraftRequestSchema.parse(request)).toThrow();
    });

    it("rejects title > 200 chars", () => {
      const request = {
        title: "x".repeat(201),
        platform: "x" as const,
      };
      expect(() => CreateDraftRequestSchema.parse(request)).toThrow();
    });

    it("rejects invalid platform", () => {
      const request = {
        title: "New Draft",
        platform: "threads" as any,
      };
      expect(() => CreateDraftRequestSchema.parse(request)).toThrow();
    });
  });

  describe("SegmentAppendRequest", () => {
    it("accepts valid request", () => {
      const request = {
        content: "Second segment",
        idempotency_key: "323e4567-e89b-12d3-a456-426614174000",
      };
      expect(SegmentAppendRequestSchema.parse(request)).toEqual(request);
    });

    it("rejects empty content", () => {
      const request = {
        content: "",
        idempotency_key: "323e4567-e89b-12d3-a456-426614174000",
      };
      expect(() => SegmentAppendRequestSchema.parse(request)).toThrow();
    });

    it("rejects content > 500 chars", () => {
      const request = {
        content: "x".repeat(501),
        idempotency_key: "323e4567-e89b-12d3-a456-426614174000",
      };
      expect(() => SegmentAppendRequestSchema.parse(request)).toThrow();
    });

    it("rejects invalid UUID", () => {
      const request = {
        content: "Second segment",
        idempotency_key: "not-a-uuid",
      };
      expect(() => SegmentAppendRequestSchema.parse(request)).toThrow();
    });
  });

  describe("PassRingRequest", () => {
    it("accepts valid request", () => {
      const request = {
        to_user_id: "user456",
        idempotency_key: "323e4567-e89b-12d3-a456-426614174000",
      };
      expect(PassRingRequestSchema.parse(request)).toEqual(request);
    });

    it("rejects invalid UUID", () => {
      const request = {
        to_user_id: "user456",
        idempotency_key: "not-a-uuid",
      };
      expect(() => PassRingRequestSchema.parse(request)).toThrow();
    });
  });

  describe("Response Shape", () => {
    it("API response wraps data in success object", () => {
      const response = {
        success: true,
        data: {
          draft_id: "123e4567-e89b-12d3-a456-426614174000",
          creator_id: "user123",
          title: "My Draft",
          platform: "x",
          status: "active",
          segments: [],
          ring_state: {
            draft_id: "123e4567-e89b-12d3-a456-426614174000",
            current_holder_id: "user123",
            holders_history: ["user123"],
            passed_at: null,
            idempotency_key: null,
          },
          created_at: "2025-12-21T10:00:00Z",
          updated_at: "2025-12-21T10:00:00Z",
          target_publish_at: null,
        },
      };

      // Verify structure
      expect(response.success).toBe(true);
      expect(response.data.draft_id).toBeDefined();
      expect(CollabDraftSchema.parse(response.data)).toBeDefined();
    });

    it("List response wraps drafts in array", () => {
      const response = {
        count: 2,
        data: [
          {
            draft_id: "123e4567-e89b-12d3-a456-426614174000",
            creator_id: "user123",
            title: "Draft 1",
            platform: "x",
            status: "active",
            segments: [],
            ring_state: {
              draft_id: "123e4567-e89b-12d3-a456-426614174000",
              current_holder_id: "user123",
              holders_history: ["user123"],
              passed_at: null,
              idempotency_key: null,
            },
            created_at: "2025-12-21T10:00:00Z",
            updated_at: "2025-12-21T10:00:00Z",
            target_publish_at: null,
          },
        ],
      };

      expect(response.count).toBe(2);
      expect(Array.isArray(response.data)).toBe(true);
      expect(response.data[0]).toBeDefined();
    });
  });
});
