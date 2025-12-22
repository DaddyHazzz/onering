/**
 * src/app/api/archetypes/public/route.ts
 * Get public archetype data (no auth required)
 */

import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const publicArchetypeSchema = z.object({
  success: z.boolean(),
  data: z.object({
    userId: z.string(),
    primary: z.string(),
    secondary: z.string().nullable(),
    explanation: z.array(z.string()).length(3),
    updatedAt: z.string(),
  }),
});

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const userId = searchParams.get("user_id");

    if (!userId) {
      return NextResponse.json(
        { error: "Missing required parameter: user_id" },
        { status: 400 }
      );
    }

    const backendUrl = `${process.env.BACKEND_URL || "http://localhost:8000"}/v1/archetypes/public?user_id=${encodeURIComponent(userId)}`;

    const backendResponse = await fetch(backendUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      return NextResponse.json(
        { error: data.error || "Failed to fetch public archetype" },
        { status: backendResponse.status }
      );
    }

    const validated = publicArchetypeSchema.parse(data);

    return NextResponse.json(validated, {
      status: 200,
      headers: {
        "Cache-Control": "public, s-maxage=120, stale-while-revalidate=300",
      },
    });
  } catch (error: any) {
    console.error("[archetypes/public] error:", error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: "Invalid archetype response format", details: error.errors },
        { status: 500 }
      );
    }

    return NextResponse.json(
      { error: error.message || "Internal server error" },
      { status: 500 }
    );
  }
}
