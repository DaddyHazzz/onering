// src/app/api/family/create/route.ts
import { NextRequest } from "next/server";
import { currentUser, clerkClient } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { z } from "zod";

const schema = z.object({
  name: z.string().min(1).max(100),
});

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    console.log("[family/create] currentUser:", userId);

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = await req.json();
    const { name } = schema.parse(body);

    // Get or create primary user in DB
    let primaryUser = await prisma.user.findUnique({
      where: { clerkId: userId },
    });

    if (!primaryUser) {
      primaryUser = await prisma.user.create({
        data: {
          clerkId: userId,
        },
      });
      console.log("[family/create] created primary user:", primaryUser.id);
    }

    // Check if primary user is verified (to auto-verify family member)
    const isVerified = primaryUser.verified;

    // Create family member with unique clerkId (for now, just use userId_memberName)
    const familyMemberId = `fm_${userId}_${Date.now()}`;

    const familyMember = await prisma.familyMember.create({
      data: {
        userId: primaryUser.id,
        clerkId: familyMemberId,
        name,
        verified: isVerified, // Auto-verify if primary is verified
      },
    });

    console.log("[family/create] created family member:", familyMember.id, { name, verified: isVerified });

    return Response.json({
      success: true,
      familyMember: {
        id: familyMember.id,
        name: familyMember.name,
        ringBalance: familyMember.ringBalance,
        verified: familyMember.verified,
      },
    });
  } catch (error: any) {
    console.error("[family/create] error:", error);
    if (error.name === "ZodError") {
      return Response.json({ error: "Invalid request" }, { status: 400 });
    }
    return Response.json({ error: error.message || "Failed to create family member" }, { status: 500 });
  }
}
