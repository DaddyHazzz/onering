import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

const currentUserMock = vi.hoisted(() => vi.fn());

vi.mock("@clerk/nextjs/server", () => ({
  currentUser: currentUserMock,
}));

const prismaMock = vi.hoisted(() => ({
  user: {
    findUnique: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
  },
}));

vi.mock("@/lib/db", () => ({
  prisma: prismaMock,
}));

const applyLedgerSpendMock = vi.hoisted(() => vi.fn());
const getTokenIssuanceModeMock = vi.hoisted(() => vi.fn());
const ensureLegacyRingWritesAllowedMock = vi.hoisted(() => vi.fn());

vi.mock("@/lib/ring-ledger", () => ({
  applyLedgerSpend: (...args: any[]) => applyLedgerSpendMock(...args),
  getTokenIssuanceMode: () => getTokenIssuanceModeMock(),
  ensureLegacyRingWritesAllowed: () => ensureLegacyRingWritesAllowedMock(),
}));

import { POST } from "../route";

describe("POST /api/ring/spend", () => {
  beforeEach(() => {
    currentUserMock.mockResolvedValue({ id: "user-1" });
    prismaMock.user.findUnique.mockResolvedValue({ id: "db-user", ringBalance: 200 });
    prismaMock.user.create.mockResolvedValue({ id: "db-user", ringBalance: 200 });
    prismaMock.user.update.mockResolvedValue({ id: "db-user", ringBalance: 100 });
    applyLedgerSpendMock.mockReset();
    getTokenIssuanceModeMock.mockReset();
    ensureLegacyRingWritesAllowedMock.mockReset();
  });

  it("shadow mode spends via ledger and returns new balance", async () => {
    getTokenIssuanceModeMock.mockReturnValue("shadow");
    applyLedgerSpendMock.mockResolvedValue({ ok: true, balanceAfter: 120 });

    const req = new NextRequest("http://localhost/api/ring/spend", {
      method: "POST",
      body: JSON.stringify({ action: "boost" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.success).toBe(true);
    expect(body.newBalance).toBe(120);
  });

  it("shadow mode blocks when insufficient balance", async () => {
    getTokenIssuanceModeMock.mockReturnValue("shadow");
    applyLedgerSpendMock.mockResolvedValue({ ok: false, error: "INSUFFICIENT_BALANCE" });

    const req = new NextRequest("http://localhost/api/ring/spend", {
      method: "POST",
      body: JSON.stringify({ action: "boost" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(400);
    expect(body.code).toBe("INSUFFICIENT_BALANCE");
  });

  it("off mode uses legacy balance updates", async () => {
    getTokenIssuanceModeMock.mockReturnValue("off");
    prismaMock.user.findUnique.mockResolvedValue({ id: "db-user", ringBalance: 250 });
    prismaMock.user.update.mockResolvedValue({ id: "db-user", ringBalance: 50 });

    const req = new NextRequest("http://localhost/api/ring/spend", {
      method: "POST",
      body: JSON.stringify({ action: "lease-username" }),
    });

    const res = await POST(req);
    const body = await res.json();

    expect(res.status).toBe(200);
    expect(body.newBalance).toBe(50);
  });
});
