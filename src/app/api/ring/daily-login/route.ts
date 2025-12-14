// src/app/api/ring/daily-login/route.ts
import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { getErrorMessage } from "@/lib/error-handler";

const DAILY_LOGIN_BONUS = 10;

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    console.log("[ring/daily-login] currentUser:", userId);

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    // Get or create user
    let user = await prisma.user.findUnique({
      where: { clerkId: userId },
    });

    if (!user) {
      user = await prisma.user.create({
        data: {
          clerkId: userId,
          ringBalance: DAILY_LOGIN_BONUS,
          lastLoginAt: new Date(),
        },
      });
      console.log("[ring/daily-login] created user with first login bonus:", user.id);
      return Response.json({
        success: true,
        ringEarned: DAILY_LOGIN_BONUS,
        newBalance: user.ringBalance,
        message: "First login! +10 RING",
      });
    }

    // Check if user already claimed today
    const now = new Date();
    const lastLogin = user.lastLoginAt;
    const isNewDay = !lastLogin || lastLogin.toDateString() !== now.toDateString();

    if (!isNewDay) {
      console.log("[ring/daily-login] user already claimed today:", userId);
      return Response.json({
        success: false,
        message: "Already claimed daily bonus today",
        newBalance: user.ringBalance,
      });
    }

    // Award daily bonus
    user = await prisma.user.update({
      where: { id: user.id },
      data: {
        ringBalance: { increment: DAILY_LOGIN_BONUS },
        lastLoginAt: now,
      },
    });

    console.log("[ring/daily-login] awarded daily bonus:", userId, { bonus: DAILY_LOGIN_BONUS, newBalance: user.ringBalance });

    return Response.json({
      success: true,
      ringEarned: DAILY_LOGIN_BONUS,
      newBalance: user.ringBalance,
      message: "Daily login bonus! +10 RING",
    });
  } catch (error: any) {
    console.error("[ring/daily-login] error:", error);
    return Response.json({ error: getErrorMessage(error) }, { status: 500 });
  }
}
