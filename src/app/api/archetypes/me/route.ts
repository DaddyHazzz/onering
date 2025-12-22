/**
 * src/app/api/archetypes/me/route.ts
 * Get user's archetype snapshot (authenticated)
 */

import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

const archetypeSnapshotSchema = z.object({
  success: z.boolean(),
  data: z.object({
    user_id: z.string(),
    primary: z.string(),
    secondary: z.string().nullable(),
    scores: z.record(z.number()),
    explanation: z.array(z.string()).length(3),
    updated_at: z.string(),
    version: z.number(),
  }),
});

export async function GET(req: NextRequest) {
  try {
    const caller = await currentUser();
    if (!caller?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const backendUrl = `${process.env.BACKEND_URL || "http://localhost:8000"}/v1/archetypes/me?user_id=${encodeURIComponent(caller.id)}`;

    const backendResponse = await fetch(backendUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      return NextResponse.json(
        { error: data.error || "Failed to fetch archetype" },
        { status: backendResponse.status }
      );
    }

    const validated = archetypeSnapshotSchema.parse(data);

    return NextResponse.json(validated, { status: 200 });
  } catch (error: any) {
    console.error("[archetypes/me] error:", error);

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
