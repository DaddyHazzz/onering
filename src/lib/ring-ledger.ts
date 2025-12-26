import { prisma } from "@/lib/db";

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
}): Promise<{ ok: boolean; mode: TokenIssuanceMode; balanceAfter?: number; error?: string }> {
  const mode = getTokenIssuanceMode();
  if (mode === "off") {
    return { ok: false, mode, error: "LEGACY_RING_WRITE_REQUIRED" };
  }
  if (params.amount <= 0) {
    return { ok: false, mode, error: "INVALID_AMOUNT" };
  }

  const legacyBalance = await getLegacyBalance(params.userId);
  const pendingTotal = await getPendingTotal(params.userId);
  const shadowDelta = await getShadowLedgerDelta(params.userId);
  const currentBalance = mode === "live"
    ? (await getLatestLedgerBalance(params.userId)) ?? legacyBalance
    : legacyBalance + pendingTotal + shadowDelta;

  if (currentBalance < params.amount) {
    return { ok: false, mode, error: "INSUFFICIENT_BALANCE" };
  }

  const balanceAfter = currentBalance - params.amount;
  await prisma.ringLedger.create({
    data: {
      userId: params.userId,
      eventType: "SPEND",
      reasonCode: params.reasonCode,
      amount: -Math.abs(params.amount),
      balanceAfter,
      metadata: params.metadata || {},
    },
  });

  if (mode === "live") {
    await prisma.user.update({
      where: { clerkId: params.userId },
      data: { ringBalance: balanceAfter },
    });
  }

  return { ok: true, mode, balanceAfter };
}

export async function applyLedgerEarn(params: {
  userId: string;
  amount: number;
  reasonCode: string;
  metadata?: Record<string, unknown>;
}): Promise<{ ok: boolean; mode: TokenIssuanceMode; balanceAfter?: number; error?: string }> {
  const mode = getTokenIssuanceMode();
  if (mode === "off") {
    return { ok: false, mode, error: "LEGACY_RING_WRITE_REQUIRED" };
  }
  if (params.amount <= 0) {
    return { ok: false, mode, error: "INVALID_AMOUNT" };
  }

  const legacyBalance = await getLegacyBalance(params.userId);
  if (mode === "shadow") {
    await prisma.ringPending.create({
      data: {
        userId: params.userId,
        amount: params.amount,
        reasonCode: params.reasonCode,
        metadata: params.metadata || {},
      },
    });
    return { ok: true, mode };
  }

  const currentBalance = (await getLatestLedgerBalance(params.userId)) ?? legacyBalance;
  const balanceAfter = currentBalance + params.amount;
  await prisma.ringLedger.create({
    data: {
      userId: params.userId,
      eventType: "EARN",
      reasonCode: params.reasonCode,
      amount: params.amount,
      balanceAfter,
      metadata: params.metadata || {},
    },
  });
  await prisma.user.update({
    where: { clerkId: params.userId },
    data: { ringBalance: balanceAfter },
  });
  return { ok: true, mode, balanceAfter };
}
