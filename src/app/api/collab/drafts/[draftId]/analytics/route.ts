import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

const draftAnalyticsSchema = z.object({
  draft_id: z.string(),
  views: z.number().nonnegative(),
  shares: z.number().nonnegative(),
  segments_count: z.number().min(1),
  contributors_count: z.number().min(1),
  ring_passes_count: z.number().nonnegative(),
  last_activity_at: z.string().nullable(),
  computed_at: z.string(),
});

const draftAnalyticsResponseSchema = z.object({
  success: z.boolean(),
  data: draftAnalyticsSchema,
});

export async function GET(
  req: NextRequest,
  { params }: { params: { draftId: string } }
) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    if (!userId) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { draftId } = params;
    if (!draftId) {
      return Response.json({ error: "Missing draftId" }, { status: 400 });
    }

    // Get optional now parameter for deterministic testing
    const searchParams = req.nextUrl.searchParams;
    const now = searchParams.get("now");

    // Proxy to backend
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const analyticsUrl = new URL(
      `/api/analytics/v1/collab/drafts/${draftId}/analytics`,
      backendUrl
    );
    if (now) {
      analyticsUrl.searchParams.set("now", now);
    }

    const response = await fetch(analyticsUrl.toString(), {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      return Response.json(
        { error: `Backend error: ${response.statusText}` },
        { status: response.status }
      );
    }

    const data = await response.json();

    // Validate response shape
    const validated = draftAnalyticsResponseSchema.parse(data);

    return Response.json(validated);
  } catch (error: any) {
    console.error("[collab/drafts/analytics] error:", error);
    return Response.json({ error: error.message }, { status: 500 });
  }
}
