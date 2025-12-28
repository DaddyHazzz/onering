import { prisma } from "@/lib/db";
import crypto from "crypto";

export type TokenIssuanceMode = "off" | "shadow" | "live";

export function getTokenIssuanceMode(): TokenIssuanceMode {
  const mode = (process.env.ONERING_TOKEN_ISSUANCE || "off").toLowerCase();
  if (mode === "shadow" || mode === "live") {
    return mode;
  }
  return "off";
}

export function assertLegacyRingWritesAllowed(): { allowed: boolean; mode: TokenIssuanceMode } {
  const mode = getTokenIssuanceMode();
  return { allowed: mode === "off", mode };
}

export function ensureLegacyRingWritesAllowed(): TokenIssuanceMode {
  const { allowed, mode } = assertLegacyRingWritesAllowed();
  if (!allowed) {
    const err = new Error("LEGACY_RING_WRITE_BLOCKED");
    (err as any).code = "LEGACY_RING_WRITE_BLOCKED";
    throw err;
  }
  return mode;
}

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export function buildIdempotencyKey(parts: string[]): string {
  const hash = crypto.createHash("sha256").update(parts.join(":")).digest("hex");
  return `ring_${hash.slice(0, 32)}`;
}

async function getLegacyBalance(userId: string): Promise<number> {
  const user = await prisma.user.findUnique({ where: { clerkId: userId }, select: { ringBalance: true } });
  return user?.ringBalance ?? 0;
}

async function getPendingTotal(userId: string): Promise<number> {
  const result = await prisma.ringPending.aggregate({
    where: { userId, status: "pending" },
    _sum: { amount: true },
  });
  return result._sum.amount ?? 0;
}

async function getShadowLedgerDelta(userId: string): Promise<number> {
  const result = await prisma.ringLedger.aggregate({
    where: { userId, eventType: { in: ["SPEND", "PENALTY", "ADJUSTMENT"] } },
    _sum: { amount: true },
  });
  return result._sum.amount ?? 0;
}

async function getLatestLedgerBalance(userId: string): Promise<number | null> {
  const row = await prisma.ringLedger.findFirst({
    where: { userId },
    orderBy: { createdAt: "desc" },
    select: { balanceAfter: true },
  });
  return row?.balanceAfter ?? null;
}

export async function getEffectiveRingBalance(userId: string): Promise<{
  mode: TokenIssuanceMode;
  balance: number;
  pendingTotal: number;
  effectiveBalance: number;
}> {
  const mode = getTokenIssuanceMode();
  const legacyBalance = await getLegacyBalance(userId);

  if (mode === "off") {
    return { mode, balance: legacyBalance, pendingTotal: 0, effectiveBalance: legacyBalance };
  }

  try {
    const res = await fetch(`${BACKEND_URL}/v1/tokens/summary/${userId}`, { cache: "no-store" });
    const data = await res.json();
    if (res.ok) {
      return {
        mode: data.mode || mode,
        balance: data.balance ?? legacyBalance,
        pendingTotal: data.pending_total ?? 0,
        effectiveBalance: data.effective_balance ?? legacyBalance,
      };
    }
  } catch (err) {
    console.warn("[ring-ledger] summary fetch failed, falling back:", err);
  }

  if (mode === "shadow") {
    const pendingTotal = await getPendingTotal(userId);
    const shadowDelta = await getShadowLedgerDelta(userId);
    const effectiveBalance = legacyBalance + pendingTotal + shadowDelta;
    return { mode, balance: legacyBalance, pendingTotal, effectiveBalance };
  }

  const ledgerBalance = (await getLatestLedgerBalance(userId)) ?? legacyBalance;
  return { mode, balance: ledgerBalance, pendingTotal: 0, effectiveBalance: ledgerBalance };
}

export async function applyLedgerSpend(params: {
  userId: string;
  amount: number;
  reasonCode: string;
  metadata?: Record<string, unknown>;
  idempotencyKey?: string;
}): Promise<{ ok: boolean; mode: TokenIssuanceMode; balanceAfter?: number; error?: string; ledgerId?: string; idempotent?: boolean }> {
  const mode = getTokenIssuanceMode();
  if (mode === "off") {
    return { ok: false, mode, error: "LEGACY_RING_WRITE_REQUIRED" };
  }
  if (params.amount <= 0) {
    return { ok: false, mode, error: "INVALID_AMOUNT" };
  }

  const idempotencyKey =
    params.idempotencyKey ||
    (params.metadata?.idempotency_key as string | undefined);

  try {
    const res = await fetch(`${BACKEND_URL}/v1/tokens/spend`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: params.userId,
        amount: params.amount,
        reason_code: params.reasonCode,
        idempotency_key: idempotencyKey,
        metadata: params.metadata || {},
      }),
    });
    const payload = await res.json();
    if (!res.ok || !payload?.ok) {
      const error = payload?.error || payload?.detail?.error || "LEDGER_SPEND_FAILED";
      return { ok: false, mode, error };
    }
    return {
      ok: true,
      mode: payload.mode || mode,
      balanceAfter: payload.balance_after,
      ledgerId: payload.ledger_id,
      idempotent: payload.idempotent,
    };
  } catch (err: any) {
    return { ok: false, mode, error: err?.message || "LEDGER_SPEND_FAILED" };
  }
}

export async function applyLedgerEarn(params: {
  userId: string;
  amount: number;
  reasonCode: string;
  metadata?: Record<string, unknown>;
  idempotencyKey?: string;
}): Promise<{ ok: boolean; mode: TokenIssuanceMode; balanceAfter?: number; error?: string; pendingId?: string; ledgerId?: string; idempotent?: boolean }> {
  const mode = getTokenIssuanceMode();
  if (mode === "off") {
    return { ok: false, mode, error: "LEGACY_RING_WRITE_REQUIRED" };
  }
  if (params.amount <= 0) {
    return { ok: false, mode, error: "INVALID_AMOUNT" };
  }

  const idempotencyKey =
    params.idempotencyKey ||
    (params.metadata?.idempotency_key as string | undefined);

  try {
    const res = await fetch(`${BACKEND_URL}/v1/tokens/earn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: params.userId,
        amount: params.amount,
        reason_code: params.reasonCode,
        idempotency_key: idempotencyKey,
        metadata: params.metadata || {},
      }),
    });
    const payload = await res.json();
    if (!res.ok || !payload?.ok) {
      const error = payload?.error || payload?.detail?.error || "LEDGER_EARN_FAILED";
      return { ok: false, mode, error };
    }
    return {
      ok: true,
      mode: payload.mode || mode,
      balanceAfter: payload.balance_after,
      pendingId: payload.pending_id,
      ledgerId: payload.ledger_id,
      idempotent: payload.idempotent,
    };
  } catch (err: any) {
    return { ok: false, mode, error: err?.message || "LEDGER_EARN_FAILED" };
  }
}
