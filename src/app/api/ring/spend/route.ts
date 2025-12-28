// src/app/api/ring/spend/route.ts
import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { applyLedgerSpend, ensureLegacyRingWritesAllowed, getTokenIssuanceMode } from "@/lib/ring-ledger";
import { z } from "zod";

const schema = z.object({
  action: z.enum(["boost", "lease-username"]),
});

const SPEND_COSTS: Record<string, number> = {
  boost: 100,
  "lease-username": 200,
};

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    console.log("[ring/spend] currentUser:", userId);

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = await req.json();
    const { action } = schema.parse(body);

    const cost = SPEND_COSTS[action];
    if (!cost) {
      return Response.json({ error: "Unknown action" }, { status: 400 });
    }

    const mode = getTokenIssuanceMode();
    if (mode !== "off") {
      const idempotencyKey = req.headers.get("Idempotency-Key") || undefined;
      const spend = await applyLedgerSpend({
        userId,
        amount: cost,
        reasonCode: `action:${action}`,
        metadata: { action },
        idempotencyKey,
      });
      if (!spend.ok) {
        const errorCode = spend.error === "INSUFFICIENT_BALANCE" ? "INSUFFICIENT_BALANCE" : "LEGACY_RING_WRITE_BLOCKED";
        const suggestedFix = spend.error === "INSUFFICIENT_BALANCE"
          ? "Reduce spend amount or earn more RING before spending."
          : "Use ledger-based spend flow when token issuance is enabled.";
        return Response.json(
          { error: "Spend blocked", code: errorCode, suggestedFix },
          { status: 400 }
        );
      }
      return Response.json({
        success: true,
        action,
        ringSpent: cost,
        newBalance: spend.balanceAfter,
        message: `${action === "boost" ? "Post boosted! dYs?" : "Username leased! dY``"}`,
      });
    }

    // Get user from database
    let user = await prisma.user.findUnique({
      where: { clerkId: userId },
    });

    if (!user) {
      // Create user if doesn't exist
      user = await prisma.user.create({
        data: { clerkId: userId },
      });
      console.log("[ring/spend] created user:", user.id);
    }

    // Check if user has enough RING
    if (user.ringBalance < cost) {
      console.warn("[ring/spend] insufficient balance:", userId, { balance: user.ringBalance, cost });
      return Response.json(
        { error: `Insufficient RING. Need ${cost}, have ${user.ringBalance}` },
        { status: 400 }
      );
    }

    // Deduct RING
    ensureLegacyRingWritesAllowed();
    user = await prisma.user.update({
      where: { id: user.id },
      data: {
        ringBalance: { decrement: cost },
      },
    });

    console.log("[ring/spend] deducted RING for action:", userId, { action, cost, newBalance: user.ringBalance });

    return Response.json({
      success: true,
      action,
      ringSpent: cost,
      newBalance: user.ringBalance,
      message: `${action === "boost" ? "Post boosted! 🚀" : "Username leased! 👑"}`,
    });
  } catch (error: any) {
    console.error("[ring/spend] error:", error);
    if (error.name === "ZodError") {
      return Response.json({ error: "Invalid action" }, { status: 400 });
    }
    return Response.json({ error: error.message || "Failed to spend RING" }, { status: 500 });
  }
}
