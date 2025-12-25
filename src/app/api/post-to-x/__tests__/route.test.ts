import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NextRequest } from "next/server";

const currentUserMock = vi.fn();

vi.mock("@clerk/nextjs/server", () => ({
  auth: () => ({ userId: null }),
  currentUser: currentUserMock,
  clerkClient: async () => ({ users: { getUser: vi.fn(), updateUser: vi.fn() } }),
}));

vi.mock("@/lib/embeddings", () => ({
  embedThread: vi.fn(async () => new Array(1536).fill(0)),
  embedUserProfile: vi.fn(async () => new Array(1536).fill(0)),
  cosineSimilarity: vi.fn(() => 0),
}));

vi.mock("ioredis", () => ({
  default: class RedisMock {
    on = vi.fn();
    zremrangebyscore = vi.fn(async () => 0);
    zcard = vi.fn(async () => 0);
    zrange = vi.fn(async () => []);
    zadd = vi.fn(async () => 1);
    expire = vi.fn(async () => 1);
  },
}));

import { POST } from "../route";

describe("POST /api/post-to-x", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    currentUserMock.mockResolvedValue(null);
    process.env = { ...originalEnv };
    vi.restoreAllMocks();
  });

  afterEach(() => {
    process.env = { ...originalEnv };
  });

  it("returns 401 when unauthenticated", async () => {
    const req = new NextRequest("http://localhost/api/post-to-x", {
      method: "POST",
      body: JSON.stringify({ content: "test" }),
    });

    const res = await POST(req);
    expect(res.status).toBe(401);
  });

  it("enforced mode blocks when receipt id missing", async () => {
    process.env.ONERING_ENFORCEMENT_MODE = "enforced";
    currentUserMock.mockResolvedValue({ id: "user-1" });

    const req = new NextRequest("http://localhost/api/post-to-x", {
      method: "POST",
      body: JSON.stringify({ content: "test content" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body.code).toBe("ENFORCEMENT_RECEIPT_REQUIRED");
  });

  it("enforced mode blocks when receipt indicates FAIL", async () => {
    process.env.ONERING_ENFORCEMENT_MODE = "enforced";
    currentUserMock.mockResolvedValue({ id: "user-1" });
    global.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({ ok: true, receipt: { qa_status: "FAIL" } }),
        { status: 200 }
      )
    ) as any;

    const req = new NextRequest("http://localhost/api/post-to-x", {
      method: "POST",
      body: JSON.stringify({ content: "test content", enforcement_request_id: "rid-1" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(403);
    expect(body.code).toBe("QA_BLOCKED");
  });

  it("enforced mode allows when receipt PASS", async () => {
    process.env.ONERING_ENFORCEMENT_MODE = "enforced";
    currentUserMock.mockResolvedValue({ id: "user-1" });
    global.fetch = vi.fn(async () =>
      new Response(
        JSON.stringify({ ok: true, receipt: { qa_status: "PASS" } }),
        { status: 200 }
      )
    ) as any;

    const req = new NextRequest("http://localhost/api/post-to-x", {
      method: "POST",
      body: JSON.stringify({ content: "test content", enforcement_request_id: "rid-1" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(500);
    expect(body.error).toMatch(/Twitter credentials not configured/);
  });

  it("advisory mode allows missing receipt but includes warning", async () => {
    process.env.ONERING_ENFORCEMENT_MODE = "advisory";
    currentUserMock.mockResolvedValue({ id: "user-1" });

    const req = new NextRequest("http://localhost/api/post-to-x", {
      method: "POST",
      body: JSON.stringify({ content: "test content" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(500);
    expect(body.warnings).toContain("ENFORCEMENT_RECEIPT_MISSING");
  });
});
