import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

const schema = z.object({
  platform: z.enum(["x", "instagram", "linkedin"]),
  draft: z.string().min(1).max(4000),
  type: z.enum(["simple", "viral_thread"]).optional().default("simple"),
  values_mode: z
    .enum(["faith_aligned", "optimistic", "confrontational", "neutral"])
    .optional()
    .default("neutral"),
  archetype: z.string().optional(),
});

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;

    if (!userId) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const data = schema.parse(body);

    // Call backend coach endpoint
    const backendResponse = await fetch(
      `${process.env.BACKEND_URL || "http://localhost:8000"}/v1/coach/feedback`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: userId,
          platform: data.platform,
          draft: data.draft,
          type: data.type,
          values_mode: data.values_mode,
          archetype: data.archetype,
        }),
      }
    );

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json();
      return Response.json(errorData, { status: backendResponse.status });
    }

    const result = await backendResponse.json();
    return Response.json(result);
  } catch (error: any) {
    console.error("[coach/feedback] error:", error);
    if (error instanceof z.ZodError) {
      return Response.json(
        { error: "Invalid request", details: error.errors },
        { status: 400 }
      );
    }
    return Response.json({ error: error.message }, { status: 500 });
  }
}
