/**
 * Collaboration types for frontend.
 * Mirrors backend models in backend/models/collab.py
 */

export type DraftStatus = "active" | "locked" | "completed";

export interface DraftSegment {
  segment_id: string;
  draft_id: string;
  user_id: string;
  content: string;
  created_at: string;
  segment_order: number;
  idempotency_key?: string;
  author_user_id?: string;
  author_display?: string;
  ring_holder_user_id_at_write?: string;
  ring_holder_display_at_write?: string;
}

export interface RingState {
  draft_id: string;
  current_holder_id: string;
  holders_history: string[];
  passed_at: string;
  last_passed_at?: string;
  idempotency_key?: string;
}

export interface CollabDraft {
  draft_id: string;
  creator_id: string;
  title: string;
  platform: string;
  status: DraftStatus;
  segments: DraftSegment[];
  ring_state: RingState;
  collaborators: string[];
  pending_invites: string[];
  created_at: string;
  updated_at: string;
  target_publish_at?: string;
  metrics?: {
    contributorsCount?: number;
    ringPassesLast24h?: number;
    avgMinutesBetweenPasses?: number;
    lastActivityAt?: string;
  };
}

export interface CollabDraftRequest {
  title: string;
  platform: string;
  initial_segment?: string;
}

export interface SegmentAppendRequest {
  content: string;
  idempotency_key: string;
}

export interface RingPassRequest {
  to_user_id: string;
  idempotency_key: string;
}

export type ErrorCode = 
  | "ring_required"
  | "permission_denied"
  | "not_found"
  | "validation_error"
  | "unknown_error";

export interface APIError {
  code: ErrorCode;
  message: string;
  status: number;
}
