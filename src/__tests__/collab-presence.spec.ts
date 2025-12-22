/**
 * src/__tests__/collab-presence.spec.ts
 * Phase 3.3a: Presence + Attribution + Ring Velocity Tests
 * 
 * Tests:
 * 1. Schema validation for attribution fields (optional)
 * 2. Schema validation for presence (last_passed_at)
 * 3. Schema validation for metrics (contributorsCount, ringPassesLast24h, avgMinutesBetweenPasses)
 * 4. formatRelativeTime() helper function logic
 * 5. No-network import guarantee (collab page imports don't trigger fetch)
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";

// Phase 3.3a Schema Extensions
const DraftSegmentWithAttributionSchema = z.object({
  segment_id: z.string().uuid(),
  draft_id: z.string().uuid(),
  user_id: z.string(),
  content: z.string().max(500),
  created_at: z.string().datetime(),
  segment_order: z.number().nonnegative(),
  idempotency_key: z.string().uuid(),
  // Phase 3.3a: Attribution fields (optional)
  author_user_id: z.string().optional(),
  author_display: z.string().optional(),
  ring_holder_user_id_at_write: z.string().optional(),
  ring_holder_display_at_write: z.string().optional(),
});

const RingStateWithPresenceSchema = z.object({
  draft_id: z.string().uuid(),
  current_holder_id: z.string(),
  holders_history: z.array(z.string()).min(1),
  passed_at: z.string().datetime().nullable(),
  idempotency_key: z.string().uuid().nullable(),
  // Phase 3.3a: Presence field (optional)
  last_passed_at: z.string().datetime().optional(),
});

const DraftMetricsSchema = z.object({
  contributorsCount: z.number().nonnegative(),
  ringPassesLast24h: z.number().nonnegative(),
  avgMinutesBetweenPasses: z.number().nullable(),
  lastActivityAt: z.string().datetime(),
});

const CollabDraftWithMetricsSchema = z.object({
  draft_id: z.string().uuid(),
  creator_id: z.string(),
  title: z.string().max(200),
  platform: z.enum(["x", "instagram", "tiktok", "youtube"]),
  status: z.enum(["active", "locked", "completed"]),
  segments: z.array(DraftSegmentWithAttributionSchema),
  ring_state: RingStateWithPresenceSchema,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  target_publish_at: z.string().datetime().nullable(),
  // Phase 3.3a: Metrics field (optional)
  metrics: DraftMetricsSchema.optional(),
});

describe("Phase 3.3a: Segment Attribution", () => {
  it("validates segment with all attribution fields present", () => {
    const segment = {
      segment_id: "550e8400-e29b-41d4-a716-446655440000",
      draft_id: "660e8400-e29b-41d4-a716-446655440000",
      user_id: "user_abc123",
      content: "First segment of the draft",
      created_at: "2025-12-21T10:00:00Z",
      segment_order: 0,
      idempotency_key: "770e8400-e29b-41d4-a716-446655440000",
      author_user_id: "user_abc123",
      author_display: "@u_abc123",
      ring_holder_user_id_at_write: "user_abc123",
      ring_holder_display_at_write: "@u_abc123",
    };

    const result = DraftSegmentWithAttributionSchema.safeParse(segment);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.author_display).toBe("@u_abc123");
      expect(result.data.ring_holder_user_id_at_write).toBe("user_abc123");
    }
  });

  it("validates segment without attribution fields (backward compatibility)", () => {
    const segment = {
      segment_id: "550e8400-e29b-41d4-a716-446655440000",
      draft_id: "660e8400-e29b-41d4-a716-446655440000",
      user_id: "user_abc123",
      content: "Legacy segment without attribution",
      created_at: "2025-12-21T10:00:00Z",
      segment_order: 0,
      idempotency_key: "770e8400-e29b-41d4-a716-446655440000",
    };

    const result = DraftSegmentWithAttributionSchema.safeParse(segment);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.author_display).toBeUndefined();
      expect(result.data.ring_holder_user_id_at_write).toBeUndefined();
    }
  });

  it("validates author_display format (@u_XXXXXX pattern)", () => {
    const segment = {
      segment_id: "550e8400-e29b-41d4-a716-446655440000",
      draft_id: "660e8400-e29b-41d4-a716-446655440000",
      user_id: "user_abc123",
      content: "Segment with formatted display name",
      created_at: "2025-12-21T10:00:00Z",
      segment_order: 0,
      idempotency_key: "770e8400-e29b-41d4-a716-446655440000",
      author_display: "@u_abc123",
    };

    const result = DraftSegmentWithAttributionSchema.safeParse(segment);
    expect(result.success).toBe(true);
    if (result.success) {
      // Verify format matches @u_XXXXXX (9 chars: @u_ + 6 hex digits)
      const display = result.data.author_display!;
      expect(display).toMatch(/^@u_[a-f0-9]{6}$/);
      expect(display.length).toBe(9);
    }
  });
});

describe("Phase 3.3a: Ring Presence", () => {
  it("validates ring_state with last_passed_at field", () => {
    const ringState = {
      draft_id: "660e8400-e29b-41d4-a716-446655440000",
      current_holder_id: "user_def456",
      holders_history: ["user_abc123", "user_def456"],
      passed_at: "2025-12-21T10:05:00Z",
      idempotency_key: "880e8400-e29b-41d4-a716-446655440000",
      last_passed_at: "2025-12-21T10:05:00Z",
    };

    const result = RingStateWithPresenceSchema.safeParse(ringState);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.last_passed_at).toBe("2025-12-21T10:05:00Z");
    }
  });

  it("validates ring_state without last_passed_at (backward compatibility)", () => {
    const ringState = {
      draft_id: "660e8400-e29b-41d4-a716-446655440000",
      current_holder_id: "user_abc123",
      holders_history: ["user_abc123"],
      passed_at: null,
      idempotency_key: null,
    };

    const result = RingStateWithPresenceSchema.safeParse(ringState);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.last_passed_at).toBeUndefined();
    }
  });

  it("validates last_passed_at is ISO datetime string", () => {
    const ringState = {
      draft_id: "660e8400-e29b-41d4-a716-446655440000",
      current_holder_id: "user_abc123",
      holders_history: ["user_abc123"],
      passed_at: null,
      idempotency_key: null,
      last_passed_at: "2025-12-21T15:30:45.123456Z",
    };

    const result = RingStateWithPresenceSchema.safeParse(ringState);
    expect(result.success).toBe(true);
  });
});

describe("Phase 3.3a: Ring Velocity Metrics", () => {
  it("validates metrics with all fields present", () => {
    const metrics = {
      contributorsCount: 3,
      ringPassesLast24h: 5,
      avgMinutesBetweenPasses: 12.5,
      lastActivityAt: "2025-12-21T15:30:00Z",
    };

    const result = DraftMetricsSchema.safeParse(metrics);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.contributorsCount).toBe(3);
      expect(result.data.ringPassesLast24h).toBe(5);
      expect(result.data.avgMinutesBetweenPasses).toBe(12.5);
    }
  });

  it("validates metrics with avgMinutesBetweenPasses as null (less than 2 passes)", () => {
    const metrics = {
      contributorsCount: 1,
      ringPassesLast24h: 0,
      avgMinutesBetweenPasses: null,
      lastActivityAt: "2025-12-21T15:30:00Z",
    };

    const result = DraftMetricsSchema.safeParse(metrics);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.avgMinutesBetweenPasses).toBeNull();
    }
  });

  it("rejects metrics with negative contributorsCount", () => {
    const metrics = {
      contributorsCount: -1,
      ringPassesLast24h: 0,
      avgMinutesBetweenPasses: null,
      lastActivityAt: "2025-12-21T15:30:00Z",
    };

    const result = DraftMetricsSchema.safeParse(metrics);
    expect(result.success).toBe(false);
  });

  it("rejects metrics with negative ringPassesLast24h", () => {
    const metrics = {
      contributorsCount: 1,
      ringPassesLast24h: -5,
      avgMinutesBetweenPasses: null,
      lastActivityAt: "2025-12-21T15:30:00Z",
    };

    const result = DraftMetricsSchema.safeParse(metrics);
    expect(result.success).toBe(false);
  });

  it("validates complete draft with metrics", () => {
    const draft = {
      draft_id: "660e8400-e29b-41d4-a716-446655440000",
      creator_id: "user_abc123",
      title: "Collaborative Twitter Thread",
      platform: "x",
      status: "active",
      segments: [
        {
          segment_id: "550e8400-e29b-41d4-a716-446655440000",
          draft_id: "660e8400-e29b-41d4-a716-446655440000",
          user_id: "user_abc123",
          content: "First segment",
          created_at: "2025-12-21T10:00:00Z",
          segment_order: 0,
          idempotency_key: "770e8400-e29b-41d4-a716-446655440000",
          author_user_id: "user_abc123",
          author_display: "@u_abc123",
        },
      ],
      ring_state: {
        draft_id: "660e8400-e29b-41d4-a716-446655440000",
        current_holder_id: "user_abc123",
        holders_history: ["user_abc123"],
        passed_at: null,
        idempotency_key: null,
        last_passed_at: "2025-12-21T10:05:00Z",
      },
      created_at: "2025-12-21T10:00:00Z",
      updated_at: "2025-12-21T10:05:00Z",
      target_publish_at: null,
      metrics: {
        contributorsCount: 1,
        ringPassesLast24h: 0,
        avgMinutesBetweenPasses: null,
        lastActivityAt: "2025-12-21T10:05:00Z",
      },
    };

    const result = CollabDraftWithMetricsSchema.safeParse(draft);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.metrics).toBeDefined();
      expect(result.data.metrics!.contributorsCount).toBe(1);
    }
  });

  it("validates draft without metrics (backward compatibility)", () => {
    const draft = {
      draft_id: "660e8400-e29b-41d4-a716-446655440000",
      creator_id: "user_abc123",
      title: "Legacy Draft",
      platform: "x",
      status: "active",
      segments: [
        {
          segment_id: "550e8400-e29b-41d4-a716-446655440000",
          draft_id: "660e8400-e29b-41d4-a716-446655440000",
          user_id: "user_abc123",
          content: "Legacy segment",
          created_at: "2025-12-21T10:00:00Z",
          segment_order: 0,
          idempotency_key: "770e8400-e29b-41d4-a716-446655440000",
        },
      ],
      ring_state: {
        draft_id: "660e8400-e29b-41d4-a716-446655440000",
        current_holder_id: "user_abc123",
        holders_history: ["user_abc123"],
        passed_at: null,
        idempotency_key: null,
      },
      created_at: "2025-12-21T10:00:00Z",
      updated_at: "2025-12-21T10:00:00Z",
      target_publish_at: null,
    };

    const result = CollabDraftWithMetricsSchema.safeParse(draft);
    expect(result.success).toBe(true);
    if (result.success) {
      expect(result.data.metrics).toBeUndefined();
    }
  });
});

describe("Phase 3.3a: formatRelativeTime() Helper", () => {
  // Mock formatRelativeTime implementation for testing
  function formatRelativeTime(isoTimestamp: string): string {
    const now = Date.now();
    const then = new Date(isoTimestamp).getTime();
    const diffMs = now - then;
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 1) return "just now";
    if (diffMinutes < 60) return `${diffMinutes}m ago`;
    const diffHours = Math.floor(diffMinutes / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  }

  it("returns 'just now' for timestamps less than 1 minute ago", () => {
    const timestamp = new Date(Date.now() - 30000).toISOString(); // 30 seconds ago
    const result = formatRelativeTime(timestamp);
    expect(result).toBe("just now");
  });

  it("returns minutes for timestamps less than 1 hour ago", () => {
    const timestamp = new Date(Date.now() - 5 * 60000).toISOString(); // 5 minutes ago
    const result = formatRelativeTime(timestamp);
    expect(result).toBe("5m ago");
  });

  it("returns hours for timestamps less than 24 hours ago", () => {
    const timestamp = new Date(Date.now() - 2 * 3600000).toISOString(); // 2 hours ago
    const result = formatRelativeTime(timestamp);
    expect(result).toBe("2h ago");
  });

  it("returns days for timestamps more than 24 hours ago", () => {
    const timestamp = new Date(Date.now() - 3 * 86400000).toISOString(); // 3 days ago
    const result = formatRelativeTime(timestamp);
    expect(result).toBe("3d ago");
  });

  it("handles edge case: exactly 60 minutes", () => {
    const timestamp = new Date(Date.now() - 60 * 60000).toISOString(); // 60 minutes ago
    const result = formatRelativeTime(timestamp);
    expect(result).toBe("1h ago");
  });

  it("handles edge case: exactly 24 hours", () => {
    const timestamp = new Date(Date.now() - 24 * 3600000).toISOString(); // 24 hours ago
    const result = formatRelativeTime(timestamp);
    expect(result).toBe("1d ago");
  });
});

describe("Phase 3.3a: No-Network Import Guarantee", () => {
  it("collab page imports do not trigger fetch", async () => {
    // Track fetch calls during import
    let fetchCalled = false;
    const originalFetch = global.fetch;
    global.fetch = (() => {
      fetchCalled = true;
      return Promise.reject(new Error("Fetch should not be called on import"));
    }) as any;

    try {
      // Import collab page module
      // Note: This test verifies that importing the module does NOT trigger API calls
      // (API calls should only happen after user interaction, not on import)
      const collabPageImport = import("../app/dashboard/collab/page");
      
      // Wait a tick to ensure any immediate effects run
      await new Promise((resolve) => setTimeout(resolve, 10));
      
      expect(fetchCalled).toBe(false);
      
      // Clean up import
      await collabPageImport;
    } finally {
      // Restore original fetch
      global.fetch = originalFetch;
    }
  });
});
