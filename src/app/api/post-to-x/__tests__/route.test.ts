import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NextRequest } from "next/server";

const currentUserMock = vi.hoisted(() => vi.fn());

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

const prismaMock = vi.hoisted(() => ({
  user: {
    findUnique: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
  },
  post: {
    create: vi.fn(),
  },
}));

vi.mock("@/lib/db", () => ({
  prisma: prismaMock,
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

vi.mock("twitter-api-v2", () => ({
  TwitterApi: class TwitterApiMock {
    v2 = {
      me: vi.fn(async () => ({ data: { id: "me" } })),
      tweet: vi.fn(async () => ({ data: { id: "tweet-1" } })),
    };
  },
}));

import { POST } from "../route";

describe("POST /api/post-to-x", () => {
  const originalEnv = { ...process.env };

  beforeEach(() => {
    currentUserMock.mockResolvedValue(null);
    process.env = { ...originalEnv };
    vi.restoreAllMocks();
    prismaMock.user.findUnique.mockResolvedValue({ id: "db-user", ringBalance: 0 });
    prismaMock.user.create.mockResolvedValue({ id: "db-user", ringBalance: 0 });
    prismaMock.user.update.mockResolvedValue({ id: "db-user", ringBalance: 50 });
    prismaMock.post.create.mockResolvedValue({ id: "post-1" });
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
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/v1/enforcement/receipts/validate")) {
        return new Response(
          JSON.stringify({ ok: false, code: "ENFORCEMENT_RECEIPT_INVALID", message: "invalid" }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ ok: false }), { status: 500 });
    }) as any;

    const req = new NextRequest("http://localhost/api/post-to-x", {
      method: "POST",
      body: JSON.stringify({ content: "test content", enforcement_request_id: "rid-1" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(403);
    expect(body.code).toBe("ENFORCEMENT_RECEIPT_INVALID");
  });

  it("enforced mode blocks when receipt expired", async () => {
    process.env.ONERING_ENFORCEMENT_MODE = "enforced";
    currentUserMock.mockResolvedValue({ id: "user-1" });
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/v1/enforcement/receipts/validate")) {
        return new Response(
          JSON.stringify({ ok: false, code: "ENFORCEMENT_RECEIPT_EXPIRED", message: "expired" }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ ok: false }), { status: 500 });
    }) as any;

    const req = new NextRequest("http://localhost/api/post-to-x", {
      method: "POST",
      body: JSON.stringify({ content: "test content", enforcement_request_id: "rid-1" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(403);
    expect(body.code).toBe("ENFORCEMENT_RECEIPT_EXPIRED");
    expect(body.suggestedFix).toBeDefined();
  });

  it("enforced mode allows when receipt PASS", async () => {
    process.env.ONERING_ENFORCEMENT_MODE = "enforced";
    currentUserMock.mockResolvedValue({ id: "user-1" });
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/v1/enforcement/receipts/validate")) {
        return new Response(
          JSON.stringify({ ok: true, receipt: { qa_status: "PASS" } }),
          { status: 200 }
        );
      }
      if (url.includes("/v1/tokens/publish")) {
        return new Response(
          JSON.stringify({ ok: true, token_result: { mode: "shadow", pending_amount: 10 } }),
          { status: 200 }
        );
      }
      return new Response(JSON.stringify({ ok: false }), { status: 500 });
    }) as any;

    const req = new NextRequest("http://localhost/api/post-to-x", {
      method: "POST",
      body: JSON.stringify({ content: "test content", enforcement_request_id: "rid-1" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(500);
    expect(body.error).toMatch(/Twitter credentials not configured/);
  });

  it("success response includes token_result when publish event succeeds", async () => {
    process.env.ONERING_ENFORCEMENT_MODE = "enforced";
    process.env.TWITTER_API_KEY = "key";
    process.env.TWITTER_API_SECRET = "secret";
    process.env.TWITTER_ACCESS_TOKEN = "token";
    process.env.TWITTER_ACCESS_TOKEN_SECRET = "token-secret";
    process.env.TWITTER_USERNAME = "tester";
    currentUserMock.mockResolvedValue({ id: "user-1" });
    global.fetch = vi.fn(async (input: RequestInfo | URL) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/v1/enforcement/receipts/validate")) {
        return new Response(
          JSON.stringify({ ok: true, receipt: { qa_status: "PASS" } }),
          { status: 200 }
        );
      }
      if (url.includes("/v1/tokens/publish")) {
        return new Response(
          JSON.stringify({ ok: true, token_result: { mode: "shadow", pending_amount: 10 } }),
          { status: 200 }
        );
      }
      if (url.includes("/v1/streaks/events/post")) {
        return new Response(JSON.stringify({ ok: true }), { status: 200 });
      }
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    }) as any;

    const req = new NextRequest("http://localhost/api/post-to-x", {
      method: "POST",
      body: JSON.stringify({ content: "test content", enforcement_request_id: "rid-1" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.token_result).toBeDefined();
    expect(body.token_result.mode).toBe("shadow");
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
