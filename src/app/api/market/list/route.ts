// src/app/api/market/list/route.ts
import { NextRequest } from "next/server";
import { prisma } from "@/lib/db";

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const category = searchParams.get("category");

    const where = { status: "active" };
    if (category && category !== "all") {
      (where as any).category = category;
    }

    const listings = await prisma.marketplaceListing.findMany({
      where,
      include: {
        user: {
          select: {
            id: true,
            verified: true,
          },
        },
      },
      orderBy: { createdAt: "desc" },
      take: 50,
    });

    console.log("[market/list] retrieved", listings.length, "listings");

    return Response.json({
      listings: listings.map((l) => ({
        id: l.id,
        title: l.title,
        description: l.description,
        priceRING: l.priceRING,
        category: l.category,
        sellerId: l.user.id,
        sellerVerified: l.user.verified,
        createdAt: l.createdAt,
      })),
    });
  } catch (error: any) {
    console.error("[market/list] error:", error);
    return Response.json(
      { error: error.message || "Failed to list listings" },
      { status: 500 }
    );
  }
}
