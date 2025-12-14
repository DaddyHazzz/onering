import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

/**
 * GET /api/monitoring/stats
 * Returns system-wide statistics for the OneRing platform.
 * Requires authentication.
 */
export async function GET(req: NextRequest) {
  const { userId } = await auth();

  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    // Placeholder stats - in production, aggregate from database
    const stats = {
      activeUsers: 42, // Count unique users from past 24h in DB
      totalRingCirculated: 12540, // Sum all RING earnings from publicMetadata
      postSuccessRate: 0.94, // Count successful_posts / total_posts
      totalPostsPublished: 328, // Count posts where status = 'published'
      totalPostsFailed: 20, // Count posts where status = 'failed'
      avgPostEarnings: 38.25, // Average of all post earnings
    };

    return NextResponse.json(stats);
  } catch (error) {
    console.error("[monitoring/stats] error:", error);
    return NextResponse.json(
      { error: "Failed to fetch stats" },
      { status: 500 }
    );
  }
}
