import { describe, it, expect, vi } from "vitest";
import { NextRequest } from "next/server";

// ✅ Mock Clerk server helpers
vi.mock("@clerk/nextjs/server", () => ({
  auth: () => ({ userId: null }),
  currentUser: async () => null,
}));

// ✅ Mock embeddings
vi.mock("@/lib/embeddings", () => ({
  embedThread: vi.fn(async () => new Array(1536).fill(0)),
  embedUserProfile: vi.fn(async () => new Array(1536).fill(0)),
  cosineSimilarity: vi.fn(() => 0),
}));

import { POST } from "../route";

describe("POST /api/post-to-x", () => {
  it("returns 401 when unauthenticated", async () => {
    const req = new NextRequest("http://localhost/api/post-to-x", {
      method: "POST",
      body: JSON.stringify({ content: "test" }),
    });

    const res = await POST(req);
    expect(res.status).toBe(401);
  });
});
