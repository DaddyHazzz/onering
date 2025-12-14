// src/app/api/ring/stake/claim/route.ts
import { NextRequest } from "next/server";
import { z } from "zod";
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";

const claimSchema = z.object({
  stakeId: z.string().uuid(),
});

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = await req.json();
    const { stakeId } = claimSchema.parse(body);

    // Find stake
    const stake = await prisma.stakingPosition.findUnique({
      where: { id: stakeId },
      include: { user: true },
    });

    if (!stake) {
      return Response.json({ error: "Stake not found" }, { status: 404 });
    }

    // Verify ownership
    if (stake.user.clerkId !== userId) {
      return Response.json({ error: "Unauthorized" }, { status: 403 });
    }

    // Calculate yield
    const now = new Date();
    const elapsedDays = Math.floor(
      (now.getTime() - stake.startDate.getTime()) / (1000 * 60 * 60 * 24)
    );

    const maturityDays = stake.durationDays;
    const claimableDays = Math.min(elapsedDays, maturityDays);

    if (claimableDays <= 0) {
      return Response.json(
        { error: "Stake has not matured yet" },
        { status: 400 }
      );
    }

    const dailyYield = (stake.amount * stake.apr) / 365;
    const totalYield = Math.floor(dailyYield * claimableDays);
    const alreadyClaimed = stake.claimedYield;
    const claimable = Math.max(0, totalYield - alreadyClaimed);

    if (claimable <= 0) {
      return Response.json(
        { error: "No claimable yield at this time" },
        { status: 400 }
      );
    }

    // Update stake and user balance
    await prisma.stakingPosition.update({
      where: { id: stakeId },
      data: {
        claimedYield: { increment: claimable },
        status: elapsedDays >= maturityDays ? "matured" : "active",
      },
    });

    await prisma.user.update({
      where: { id: stake.userId },
      data: {
        ringBalance: { increment: claimable },
      },
    });

    console.log(
      `[ring/stake/claim] user ${userId} claimed ${claimable} RING from stake ${stakeId}`
    );

    return Response.json({
      success: true,
      claimedYield: claimable,
      totalYield,
      elapsedDays,
      maturityDays,
      nextClaimableAt: new Date(
        stake.startDate.getTime() + maturityDays * 24 * 60 * 60 * 1000
      ).toISOString(),
    });
  } catch (error: any) {
    console.error("[ring/stake/claim] error:", error);
    return Response.json(
      { error: error.message || "Failed to claim yield" },
      { status: 500 }
    );
  }
}
