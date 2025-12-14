// src/app/api/ring/stake/list/route.ts
import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";

export async function GET(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    // Find user
    const dbUser = await prisma.user.findUnique({
      where: { clerkId: userId },
      include: {
        stakingPositions: {
          where: { status: { in: ["active", "matured"] } },
          orderBy: { createdAt: "desc" },
        },
      },
    });

    if (!dbUser) {
      return Response.json(
        { stakes: [], totalStaked: 0, totalYieldClaimed: 0 },
        { status: 200 }
      );
    }

    const now = new Date();
    const enrichedStakes = dbUser.stakingPositions.map((stake: any) => {
      const elapsedDays = Math.floor(
        (now.getTime() - stake.startDate.getTime()) / (1000 * 60 * 60 * 24)
      );
      const dailyYield = (stake.amount * stake.apr) / 365;
      const totalYield = Math.floor(dailyYield * stake.durationDays);
      const claimable = Math.max(0, totalYield - stake.claimedYield);
      const isMatured = elapsedDays >= stake.durationDays;

      return {
        id: stake.id,
        amount: stake.amount,
        apr: stake.apr,
        durationDays: stake.durationDays,
        startDate: stake.startDate.toISOString(),
        maturityDate: new Date(
          stake.startDate.getTime() + stake.durationDays * 24 * 60 * 60 * 1000
        ).toISOString(),
        claimedYield: stake.claimedYield,
        claimableYield: claimable,
        totalYield,
        elapsedDays,
        isMatured,
        status: stake.status,
      };
    });

    const totalStaked = enrichedStakes.reduce((sum: number, s: any) => sum + s.amount, 0);
    const totalYieldClaimed = enrichedStakes.reduce(
      (sum: number, s: any) => sum + s.claimedYield,
      0
    );

    console.log(
      `[ring/stake/list] fetched ${enrichedStakes.length} stakes for user ${userId}`
    );

    return Response.json({
      success: true,
      stakes: enrichedStakes,
      totalStaked,
      totalYieldClaimed,
    });
  } catch (error: any) {
    console.error("[ring/stake/list] error:", error);
    return Response.json(
      { error: error.message || "Failed to fetch stakes" },
      { status: 500 }
    );
  }
}
