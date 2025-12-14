// src/app/api/family/list/route.ts
import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { getErrorMessage } from "@/lib/error-handler";

export async function GET(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    console.log("[family/list] currentUser:", userId);

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    // Get primary user
    const primaryUser = await prisma.user.findUnique({
      where: { clerkId: userId },
      include: {
        familyMembers: true,
      },
    });

    if (!primaryUser) {
      return Response.json({
        primaryUser: null,
        familyMembers: [],
        combinedRingBalance: 0,
      });
    }

    // Calculate combined ring balance
    const familyRing = primaryUser.familyMembers.reduce((sum: number, member: any) => sum + member.ringBalance, 0);
    const combinedRingBalance = primaryUser.ringBalance + familyRing;

    return Response.json({
      primaryUser: {
        id: primaryUser.id,
        ringBalance: primaryUser.ringBalance,
        verified: primaryUser.verified,
      },
      familyMembers: primaryUser.familyMembers.map((m: any) => ({
        id: m.id,
        name: m.name,
        ringBalance: m.ringBalance,
        verified: m.verified,
      })),
      combinedRingBalance,
    });
  } catch (error: any) {
    console.error("[family/list] error:", error);
    return Response.json({ error: getErrorMessage(error) }, { status: 500 });
  }
}
