/**
 * src/features/collab/joinedBanner.ts
 * Helper functions for "joined draft" banner logic (Phase 3.3b)
 */

export interface JoinedBannerState {
  userId: string;
  draftId: string;
  isRingHolder: boolean;
  ringHolderDisplay: string;
}

/**
 * Generate localStorage key for banner dismissal
 */
export function joinedBannerKey(userId: string, draftId: string): string {
  return `collab_joined_seen:${userId}:${draftId}`;
}

/**
 * Check if banner should be shown
 * Returns true if joined=1 param exists AND banner not yet dismissed
 */
export function shouldShowJoinedBanner(
  storage: Storage,
  userId: string,
  draftId: string,
  joinedParam: string | null
): boolean {
  if (joinedParam !== "1") return false;
  const key = joinedBannerKey(userId, draftId);
  return storage.getItem(key) === null;
}

/**
 * Mark banner as seen (persist dismissal)
 */
export function dismissJoinedBanner(storage: Storage, userId: string, draftId: string): void {
  const key = joinedBannerKey(userId, draftId);
  storage.setItem(key, "1");
}

/**
 * Generate banner message based on ring holder status
 */
export function getJoinedBannerMessage(state: JoinedBannerState): string {
  if (state.isRingHolder) {
    return "You joined the thread — it's your turn 🔴";
  }
  return `You joined the thread — ring is with ${state.ringHolderDisplay}`;
}
