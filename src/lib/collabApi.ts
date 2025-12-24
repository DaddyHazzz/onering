/**
 * Frontend API client for collaboration endpoints.
 * 
 * Strongly typed wrapper around /v1/collab/* endpoints.
 * Automatically injects X-User-Id header.
 * Handles error normalization and ring-required detection.
 */

import { 
  CollabDraft, 
  DraftSegment, 
  CollabDraftRequest, 
  SegmentAppendRequest, 
  RingPassRequest,
  APIError 
} from "@/types/collab";

const BASE_URL = "/v1/collab";

/**
 * Get current user ID from localStorage.
 * Note: This is temporary auth for Phase 5.x. Production will use Clerk.
 */
function getUserId(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return localStorage.getItem("test_user_id") || "anonymous";
}

/**
 * Fetch with X-User-Id header automatically injected.
 */
async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<any> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    "X-User-Id": getUserId(),
    ...(options.headers || {}),
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  const body = await response.json();

  // Normalize error responses
  if (!response.ok) {
    const error: APIError = {
      code: body.error?.code || "unknown_error",
      message: body.error?.message || "An error occurred",
      status: response.status,
    };
    throw error;
  }

  return body;
}

/**
 * List all drafts involving the current user.
 */
export async function listDrafts(): Promise<CollabDraft[]> {
  const response = await apiFetch("/drafts");
  return response.data || [];
}

/**
 * Create a new draft.
 */
export async function createDraft(
  request: CollabDraftRequest
): Promise<CollabDraft> {
  const response = await apiFetch("/drafts", {
    method: "POST",
    body: JSON.stringify(request),
  });
  return response.data;
}

/**
 * Get draft detail by ID.
 */
export async function getDraft(draftId: string): Promise<CollabDraft> {
  const response = await apiFetch(`/drafts/${draftId}`);
  return response.data;
}

/**
 * Append segment to draft (idempotent).
 * 
 * Throws APIError with code="ring_required" if user is not ring holder.
 */
export async function appendSegment(
  draftId: string,
  request: SegmentAppendRequest
): Promise<CollabDraft> {
  try {
    const response = await apiFetch(`/drafts/${draftId}/segments`, {
      method: "POST",
      body: JSON.stringify(request),
    });
    return response.data;
  } catch (error: any) {
    // Re-throw with code preserved for ring_required detection
    if (error.code === "ring_required") {
      throw error;
    }
    throw error;
  }
}

/**
 * Pass ring to another user (idempotent).
 */
export async function passRing(
  draftId: string,
  request: RingPassRequest
): Promise<CollabDraft> {
  const response = await apiFetch(`/drafts/${draftId}/pass-ring`, {
    method: "POST",
    body: JSON.stringify(request),
  });
  return response.data;
}

/**
 * Add collaborator to draft (creator only).
 */
export async function addCollaborator(
  draftId: string,
  collaboratorId: string,
  role: string = "contributor"
): Promise<CollabDraft> {
  const response = await apiFetch(`/drafts/${draftId}/collaborators`, {
    method: "POST",
    body: JSON.stringify({}),
  });
  return response.data;
}

/**
 * Check if error is a ring_required error.
 */
export function isRingRequiredError(error: unknown): error is APIError {
  return (
    typeof error === "object" &&
    error !== null &&
    "code" in error &&
    (error as any).code === "ring_required"
  );
}
