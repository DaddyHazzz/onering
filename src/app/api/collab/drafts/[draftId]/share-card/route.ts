import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

const shareCardSchema = z.object({
  draft_id: z.string(),
  title: z.string(),
  subtitle: z.string(),
  metrics: z.object({
    contributors_count: z.number(),
    ring_passes_last_24h: z.number(),
    avg_minutes_between_passes: z.number().nullable(),
    segments_count: z.number(),
  }),
  contributors: z.array(z.string()),
  top_line: z.string(),
  cta: z.object({
    label: z.string(),
    url: z.string().startsWith("/dashboard/collab"),
  }),
  theme: z.object({
    bg: z.string(),
    accent: z.string(),
  }),
  generated_at: z.string(),
});

export type ShareCard = z.infer<typeof shareCardSchema>;

export async function GET(
  req: NextRequest,
  { params }: { params: { draftId: string } }
) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    if (!userId)
      return Response.json({ error: "Unauthorized" }, { status: 401 });

    const { draftId } = params;
    if (!draftId)
      return Response.json({ error: "Missing draftId" }, { status: 400 });

    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";
    const shareCardUrl = new URL(
      `/v1/collab/drafts/${draftId}/share-card`,
      backendUrl
    );
    shareCardUrl.searchParams.set("viewer_id", userId);
    shareCardUrl.searchParams.set("style", "default");

    const response = await fetch(shareCardUrl.toString(), {
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
    if (data.data) {
      const validated = shareCardSchema.parse(data.data);
      return Response.json({
        success: true,
        data: validated,
      });
    }

    return Response.json(
      { error: "Invalid share card response from backend" },
      { status: 500 }
    );
  } catch (error: any) {
    console.error("[share-card] error:", error);
    if (error instanceof z.ZodError) {
      return Response.json(
        { error: "Invalid share card format", details: error.errors },
        { status: 500 }
      );
    }
    return Response.json({ error: error.message }, { status: 500 });
  }
}
