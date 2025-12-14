// src/app/api/market/create/route.ts
import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { z } from "zod";

const schema = z.object({
  title: z.string().min(1).max(200),
  description: z.string().min(10).max(2000),
  priceRING: z.number().int().min(1).max(100000),
  category: z.enum(["template", "service", "tool", "other"]).optional(),
});

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    console.log("[market/create] currentUser:", userId);

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = await req.json();
    const { title, description, priceRING, category } = schema.parse(body);

    // Get or create user in DB
    let dbUser = await prisma.user.findUnique({
      where: { clerkId: userId },
    });

    if (!dbUser) {
      dbUser = await prisma.user.create({
        data: { clerkId: userId },
      });
      console.log("[market/create] created user:", dbUser.id);
    }

    // Create listing
    const listing = await prisma.marketplaceListing.create({
      data: {
        userId: dbUser.id,
        title,
        description,
        priceRING,
        category: category || "other",
      },
    });

    console.log("[market/create] created listing:", listing.id);

    return Response.json({
      success: true,
      listing: {
        id: listing.id,
        title: listing.title,
        description: listing.description,
        priceRING: listing.priceRING,
        category: listing.category,
      },
    });
  } catch (error: any) {
    console.error("[market/create] error:", error);
    if (error.name === "ZodError") {
      return Response.json({ error: "Invalid request" }, { status: 400 });
    }
    return Response.json(
      { error: error.message || "Failed to create listing" },
      { status: 500 }
    );
  }
}
