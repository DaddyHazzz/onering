// src/app/api/market/purchase/route.ts
import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { z } from "zod";

const schema = z.object({
  listingId: z.string().min(1),
});

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const buyerId = caller?.id;
    console.log("[market/purchase] currentUser:", buyerId);

    if (!buyerId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    const body = await req.json();
    const { listingId } = schema.parse(body);

    // Get listing
    const listing = await prisma.marketplaceListing.findUnique({
      where: { id: listingId },
      include: { user: true },
    });

    if (!listing) {
      return Response.json({ error: "Listing not found" }, { status: 404 });
    }

    if (listing.status !== "active") {
      return Response.json(
        { error: "Listing is no longer available" },
        { status: 400 }
      );
    }

    if (listing.user.clerkId === buyerId) {
      return Response.json(
        { error: "Cannot purchase your own listing" },
        { status: 400 }
      );
    }

    // Get buyer
    let buyer = await prisma.user.findUnique({
      where: { clerkId: buyerId },
    });

    if (!buyer) {
      buyer = await prisma.user.create({
        data: { clerkId: buyerId },
      });
    }

    // Check buyer has enough RING
    if (buyer.ringBalance < listing.priceRING) {
      return Response.json(
        { error: `Insufficient RING. Need ${listing.priceRING}, have ${buyer.ringBalance}` },
        { status: 400 }
      );
    }

    // Deduct from buyer, credit to seller
    await prisma.user.update({
      where: { id: buyer.id },
      data: { ringBalance: { decrement: listing.priceRING } },
    });

    await prisma.user.update({
      where: { id: listing.userId },
      data: { ringBalance: { increment: listing.priceRING } },
    });

    // Mark listing as sold
    await prisma.marketplaceListing.update({
      where: { id: listingId },
      data: { status: "sold" },
    });

    console.log(
      "[market/purchase] transaction complete:",
      buyerId,
      "→",
      listing.user.clerkId,
      listing.priceRING,
      "RING"
    );

    return Response.json({
      success: true,
      message: `Purchased "${listing.title}" for ${listing.priceRING} RING`,
      newBuyerBalance: (await prisma.user.findUnique({ where: { id: buyer.id } }))
        ?.ringBalance,
    });
  } catch (error: any) {
    console.error("[market/purchase] error:", error);
    if (error.name === "ZodError") {
      return Response.json({ error: "Invalid request" }, { status: 400 });
    }
    return Response.json(
      { error: error.message || "Purchase failed" },
      { status: 500 }
    );
  }
}
