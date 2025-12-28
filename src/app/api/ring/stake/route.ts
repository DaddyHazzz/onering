// src/app/api/ring/stake/route.ts
import { NextRequest } from "next/server";
import { z } from "zod";
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { applyLedgerSpend, ensureLegacyRingWritesAllowed, getTokenIssuanceMode } from "@/lib/ring-ledger";

const stakeSchema = z.object({
  amount: z.number().int().positive("Amount must be positive"),
  durationDays: z.number().int().positive("Duration must be positive"),
  apr: z.number().positive().optional().default(5.0),
});

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = await req.json();
    const { amount, durationDays, apr } = stakeSchema.parse(body);

    // Find user
    const dbUser = await prisma.user.findUnique({
      where: { clerkId: userId },
    });

    if (!dbUser) {
      return Response.json({ error: "User not found" }, { status: 404 });
    }

    const mode = getTokenIssuanceMode();
    if (mode === "off") {
      ensureLegacyRingWritesAllowed();
      if (dbUser.ringBalance < amount) {
        return Response.json(
          { error: `Insufficient RING. Need ${amount}, have ${dbUser.ringBalance}` },
          { status: 400 }
        );
      }
    } else {
      const idempotencyKey = req.headers.get("Idempotency-Key") || undefined;
      const spend = await applyLedgerSpend({
        userId,
        amount,
        reasonCode: "stake",
        metadata: { duration_days: durationDays, apr },
        idempotencyKey,
      });
      if (!spend.ok) {
        return Response.json(
          { error: "Stake blocked", code: spend.error || "LEGACY_RING_WRITE_BLOCKED" },
          { status: 400 }
        );
      }
    }

    // Create staking position
    const stake = await prisma.stakingPosition.create({
      data: {
        userId: dbUser.id,
        amount,
        durationDays,
        apr,
        status: "active",
      },
    });

    if (mode === "off") {
      // Deduct from balance (legacy off mode only)
      ensureLegacyRingWritesAllowed();
      await prisma.user.update({
        where: { id: dbUser.id },
        data: {
          ringBalance: { decrement: amount },
        },
      });
    }

    const dailyYield = (amount * apr) / 365;
    const totalYield = dailyYield * durationDays;

    console.log(
      `[ring/stake] user ${userId} staked ${amount} RING for ${durationDays} days at ${apr}% APR`
    );
    console.log(`[ring/stake] estimated yield: ${totalYield.toFixed(2)} RING`);

    return Response.json({
      success: true,
      stakeId: stake.id,
      amount,
      durationDays,
      apr,
      estimatedYield: Math.floor(totalYield),
      maturityDate: new Date(
        Date.now() + durationDays * 24 * 60 * 60 * 1000
      ).toISOString(),
    });
  } catch (error: any) {
    console.error("[ring/stake] error:", error);
    return Response.json(
      { error: getErrorMessage(error) },
      { status: 500 }
    );
  }
}
