/**
 * src/__tests__/collab-joined-banner.spec.ts
 * Phase 3.3b: Joined banner helper functions tests
 */

import { describe, it, expect } from "vitest";
import {
  joinedBannerKey,
  shouldShowJoinedBanner,
  dismissJoinedBanner,
  getJoinedBannerMessage,
} from "../features/collab/joinedBanner";

describe("Phase 3.3b: Joined Banner Helpers", () => {
  describe("joinedBannerKey", () => {
    it("generates deterministic key from userId and draftId", () => {
      const key1 = joinedBannerKey("user123", "draft456");
      const key2 = joinedBannerKey("user123", "draft456");
      expect(key1).toBe(key2);
      expect(key1).toBe("collab_joined_seen:user123:draft456");
    });

    it("generates different keys for different users", () => {
      const key1 = joinedBannerKey("user123", "draft456");
      const key2 = joinedBannerKey("user789", "draft456");
      expect(key1).not.toBe(key2);
    });

    it("generates different keys for different drafts", () => {
      const key1 = joinedBannerKey("user123", "draft456");
      const key2 = joinedBannerKey("user123", "draft789");
      expect(key1).not.toBe(key2);
    });
  });

  describe("shouldShowJoinedBanner", () => {
    it("returns false if joined param is not '1'", () => {
      const mockStorage = {
        getItem: () => null,
        setItem: () => {},
        removeItem: () => {},
        clear: () => {},
        key: () => null,
        length: 0,
      } as Storage;

      expect(shouldShowJoinedBanner(mockStorage, "user123", "draft456", null)).toBe(false);
      expect(shouldShowJoinedBanner(mockStorage, "user123", "draft456", "0")).toBe(false);
      expect(shouldShowJoinedBanner(mockStorage, "user123", "draft456", "true")).toBe(false);
    });

    it("returns false if banner already dismissed", () => {
      const mockStorage = {
        getItem: (key: string) => (key === "collab_joined_seen:user123:draft456" ? "1" : null),
        setItem: () => {},
        removeItem: () => {},
        clear: () => {},
        key: () => null,
        length: 0,
      } as Storage;

      expect(shouldShowJoinedBanner(mockStorage, "user123", "draft456", "1")).toBe(false);
    });

    it("returns true if joined=1 and banner not yet dismissed", () => {
      const mockStorage = {
        getItem: () => null,
        setItem: () => {},
        removeItem: () => {},
        clear: () => {},
        key: () => null,
        length: 0,
      } as Storage;

      expect(shouldShowJoinedBanner(mockStorage, "user123", "draft456", "1")).toBe(true);
    });
  });

  describe("dismissJoinedBanner", () => {
    it("sets localStorage key to '1'", () => {
      let storedKey: string | null = null;
      let storedValue: string | null = null;

      const mockStorage = {
        getItem: () => null,
        setItem: (key: string, value: string) => {
          storedKey = key;
          storedValue = value;
        },
        removeItem: () => {},
        clear: () => {},
        key: () => null,
        length: 0,
      } as Storage;

      dismissJoinedBanner(mockStorage, "user123", "draft456");

      expect(storedKey).toBe("collab_joined_seen:user123:draft456");
      expect(storedValue).toBe("1");
    });
  });

  describe("getJoinedBannerMessage", () => {
    it("returns 'your turn' message if user is ring holder", () => {
      const message = getJoinedBannerMessage({
        userId: "user123",
        draftId: "draft456",
        isRingHolder: true,
        ringHolderDisplay: "user123",
      });

      expect(message).toBe("You joined the thread — it's your turn 🔴");
    });

    it("returns 'ring is with X' message if user is not ring holder", () => {
      const message = getJoinedBannerMessage({
        userId: "user123",
        draftId: "draft456",
        isRingHolder: false,
        ringHolderDisplay: "@u_abc123",
      });

      expect(message).toBe("You joined the thread — ring is with @u_abc123");
    });

    it("includes ring holder display name in message", () => {
      const message = getJoinedBannerMessage({
        userId: "user123",
        draftId: "draft456",
        isRingHolder: false,
        ringHolderDisplay: "@u_def456",
      });

      expect(message).toContain("@u_def456");
    });
  });

  describe("Banner Integration Flow", () => {
    it("full lifecycle: show -> dismiss -> don't show again", () => {
      const store: { [key: string]: string } = {};
      const mockStorage = {
        getItem: (key: string) => store[key] || null,
        setItem: (key: string, value: string) => {
          store[key] = value;
        },
        removeItem: (key: string) => {
          delete store[key];
        },
        clear: () => {},
        key: () => null,
        length: 0,
      } as Storage;

      const userId = "user123";
      const draftId = "draft456";

      // First visit with joined=1
      expect(shouldShowJoinedBanner(mockStorage, userId, draftId, "1")).toBe(true);

      // User dismisses banner
      dismissJoinedBanner(mockStorage, userId, draftId);

      // Second visit with joined=1 (after dismissal)
      expect(shouldShowJoinedBanner(mockStorage, userId, draftId, "1")).toBe(false);

      // Visit without joined param
      expect(shouldShowJoinedBanner(mockStorage, userId, draftId, null)).toBe(false);
    });

    it("different users see banner independently", () => {
      const store: { [key: string]: string } = {};
      const mockStorage = {
        getItem: (key: string) => store[key] || null,
        setItem: (key: string, value: string) => {
          store[key] = value;
        },
        removeItem: () => {},
        clear: () => {},
        key: () => null,
        length: 0,
      } as Storage;

      const draftId = "draft456";

      // User1 dismisses banner
      dismissJoinedBanner(mockStorage, "user1", draftId);

      // User1 shouldn't see banner
      expect(shouldShowJoinedBanner(mockStorage, "user1", draftId, "1")).toBe(false);

      // User2 should still see banner
      expect(shouldShowJoinedBanner(mockStorage, "user2", draftId, "1")).toBe(true);
    });
  });
});
