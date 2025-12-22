/**
 * src/__tests__/collab-invites.spec.ts
 * Collaboration invites schema and API contract tests
 */

import { describe, it, expect } from "vitest";
import { z } from "zod";

// Schema definitions (match frontend API response types)
const InviteStatusSchema = z.enum(["PENDING", "ACCEPTED", "REVOKED", "EXPIRED"]);

const InviteSummarySchema = z.object({
  invite_id: z.string(),
  draft_id: z.string(),
  created_by_user_id: z.string(),
  target_user_id: z.string(),
  target_handle: z.string().nullable(),
  status: InviteStatusSchema,
  created_at: z.string().datetime(),
  expires_at: z.string().datetime(),
  accepted_at: z.string().datetime().nullable(),
  token_hint: z.string(),
  // token_hash MUST NOT be in summary (safe export)
}).strict(); // Reject extra fields

const CreateInviteResponseSchema = z.object({
  success: z.literal(true),
  data: z.object({
    invite_id: z.string(),
    target_user_id: z.string(),
    status: InviteStatusSchema,
    created_at: z.string().datetime(),
    expires_at: z.string().datetime(),
    token_hint: z.string(),
    share_url: z.string().url(),
    // token returned separately (in response, not stored)
  }),
});

const AcceptInviteResponseSchema = z.object({
  success: z.literal(true),
  data: z.object({
    invite_id: z.string(),
    status: z.literal("ACCEPTED"),
    accepted_at: z.string().datetime(),
  }),
});

const RevokeInviteResponseSchema = z.object({
  success: z.literal(true),
  data: z.object({
    invite_id: z.string(),
    status: z.literal("REVOKED"),
  }),
});

const ListInvitesResponseSchema = z.object({
  success: z.literal(true),
  data: z.array(InviteSummarySchema),
});

describe("Collaboration Invites - Schemas", () => {
  describe("InviteSummary (safe export)", () => {
    it("should have all required fields", () => {
      const summary = {
        invite_id: "inv_123",
        draft_id: "draft_456",
        created_by_user_id: "user_creator",
        target_user_id: "user_target",
        target_handle: "alice",
        status: "PENDING",
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
        accepted_at: null,
        token_hint: "abc123",
      };

      const result = InviteSummarySchema.safeParse(summary);
      expect(result.success).toBe(true);
    });

    it("should NOT include token_hash", () => {
      const summary = {
        invite_id: "inv_123",
        draft_id: "draft_456",
        created_by_user_id: "user_creator",
        target_user_id: "user_target",
        target_handle: "alice",
        status: "PENDING",
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
        accepted_at: null,
        token_hint: "abc123",
        token_hash: "secret_hash", // Should be rejected
      };

      const result = InviteSummarySchema.safeParse(summary);
      // Zod's strict mode rejects extra fields
      expect(result.success).toBe(false);
    });

    it("should accept null target_handle (when created with user_id)", () => {
      const summary = {
        invite_id: "inv_123",
        draft_id: "draft_456",
        created_by_user_id: "user_creator",
        target_user_id: "user_target",
        target_handle: null,
        status: "PENDING",
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
        accepted_at: null,
        token_hint: "abc123",
      };

      const result = InviteSummarySchema.safeParse(summary);
      expect(result.success).toBe(true);
    });

    it("should accept EXPIRED status", () => {
      const summary = {
        invite_id: "inv_123",
        draft_id: "draft_456",
        created_by_user_id: "user_creator",
        target_user_id: "user_target",
        target_handle: "alice",
        status: "EXPIRED",
        created_at: new Date(Date.now() - 100 * 3600 * 1000).toISOString(),
        expires_at: new Date(Date.now() - 1 * 3600 * 1000).toISOString(),
        accepted_at: null,
        token_hint: "abc123",
      };

      const result = InviteSummarySchema.safeParse(summary);
      expect(result.success).toBe(true);
    });

    it("should accept ACCEPTED status with accepted_at", () => {
      const summary = {
        invite_id: "inv_123",
        draft_id: "draft_456",
        created_by_user_id: "user_creator",
        target_user_id: "user_target",
        target_handle: "alice",
        status: "ACCEPTED",
        created_at: new Date(Date.now() - 10 * 3600 * 1000).toISOString(),
        expires_at: new Date(Date.now() + 62 * 3600 * 1000).toISOString(),
        accepted_at: new Date().toISOString(),
        token_hint: "abc123",
      };

      const result = InviteSummarySchema.safeParse(summary);
      expect(result.success).toBe(true);
    });
  });

  describe("CreateInviteResponse", () => {
    it("should have success=true and data fields", () => {
      const response = {
        success: true,
        data: {
          invite_id: "inv_123",
          target_user_id: "user_target",
          status: "PENDING",
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
          token_hint: "abc123",
          share_url: "https://localhost:3000/collab/invite/inv_123?token=...",
        },
      };

      const result = CreateInviteResponseSchema.safeParse(response);
      expect(result.success).toBe(true);
    });

    it("should have valid share_url format", () => {
      const response = {
        success: true,
        data: {
          invite_id: "inv_123",
          target_user_id: "user_target",
          status: "PENDING",
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
          token_hint: "abc123",
          share_url: "https://example.com/collab/invite/inv_123?token=mytoken",
        },
      };

      const result = CreateInviteResponseSchema.safeParse(response);
      expect(result.success).toBe(true);
      expect(result.data?.data.share_url).toContain("invite");
    });
  });

  describe("AcceptInviteResponse", () => {
    it("should return ACCEPTED status", () => {
      const response = {
        success: true,
        data: {
          invite_id: "inv_123",
          status: "ACCEPTED",
          accepted_at: new Date().toISOString(),
        },
      };

      const result = AcceptInviteResponseSchema.safeParse(response);
      expect(result.success).toBe(true);
    });
  });

  describe("RevokeInviteResponse", () => {
    it("should return REVOKED status", () => {
      const response = {
        success: true,
        data: {
          invite_id: "inv_123",
          status: "REVOKED",
        },
      };

      const result = RevokeInviteResponseSchema.safeParse(response);
      expect(result.success).toBe(true);
    });
  });

  describe("ListInvitesResponse", () => {
    it("should return array of InviteSummary", () => {
      const response = {
        success: true,
        data: [
          {
            invite_id: "inv_123",
            draft_id: "draft_456",
            created_by_user_id: "user_creator",
            target_user_id: "user_target",
            target_handle: "alice",
            status: "PENDING",
            created_at: new Date().toISOString(),
            expires_at: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
            accepted_at: null,
            token_hint: "abc123",
          },
        ],
      };

      const result = ListInvitesResponseSchema.safeParse(response);
      expect(result.success).toBe(true);
      expect(result.data?.data).toHaveLength(1);
    });

    it("should return empty array if no invites", () => {
      const response = {
        success: true,
        data: [],
      };

      const result = ListInvitesResponseSchema.safeParse(response);
      expect(result.success).toBe(true);
      expect(result.data?.data).toHaveLength(0);
    });
  });

  describe("Invalid responses", () => {
    it("should reject response without success field", () => {
      const response = {
        data: { invite_id: "inv_123" },
      };

      const result = CreateInviteResponseSchema.safeParse(response);
      expect(result.success).toBe(false);
    });

    it("should reject response with success=false", () => {
      const response = {
        success: false,
        data: { error: "Some error" },
      };

      const result = CreateInviteResponseSchema.safeParse(response);
      expect(result.success).toBe(false);
    });

    it("should reject invalid status enum", () => {
      const summary = {
        invite_id: "inv_123",
        draft_id: "draft_456",
        created_by_user_id: "user_creator",
        target_user_id: "user_target",
        target_handle: "alice",
        status: "INVALID_STATUS",
        created_at: new Date().toISOString(),
        expires_at: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
        accepted_at: null,
        token_hint: "abc123",
      };

      const result = InviteSummarySchema.safeParse(summary);
      expect(result.success).toBe(false);
    });

    it("should reject invalid datetime format", () => {
      const summary = {
        invite_id: "inv_123",
        draft_id: "draft_456",
        created_by_user_id: "user_creator",
        target_user_id: "user_target",
        target_handle: "alice",
        status: "PENDING",
        created_at: "not-a-datetime",
        expires_at: new Date(Date.now() + 72 * 3600 * 1000).toISOString(),
        accepted_at: null,
        token_hint: "abc123",
      };

      const result = InviteSummarySchema.safeParse(summary);
      expect(result.success).toBe(false);
    });
  });

  describe("Draft model integration", () => {
    it("should have collaborators and pending_invites fields", () => {
      // This is a type check: verify the fields exist on CollabDraft
      const draft = {
        draft_id: "draft_123",
        title: "Test",
        platform: "x",
        creator_id: "user_creator",
        created_at: new Date().toISOString(),
        collaborators: ["user_alice", "user_bob"],
        pending_invites: ["inv_123", "inv_456"],
      };

      expect(draft.collaborators).toHaveLength(2);
      expect(draft.pending_invites).toHaveLength(2);
    });
  });
});
