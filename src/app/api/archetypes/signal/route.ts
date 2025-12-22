/**
 * src/app/api/archetypes/signal/route.ts
 * Record archetype signal (authenticated)
 */

import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

const signalRequestSchema = z.object({
  source: z.enum(["coach", "challenge", "post"]),
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  payload: z.record(z.any()).optional(),
});

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    if (!caller?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const validated = signalRequestSchema.parse(body);

    const backendUrl = `${process.env.BACKEND_URL || "http://localhost:8000"}/v1/archetypes/signal`;

    const backendResponse = await fetch(backendUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: caller.id,
        source: validated.source,
        date: validated.date,
        payload: validated.payload || {},
      }),
    });

    const data = await backendResponse.json();

    if (!backendResponse.ok) {
      return NextResponse.json(
        { error: data.error || "Failed to record signal" },
        { status: backendResponse.status }
      );
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error: any) {
    console.error("[archetypes/signal] error:", error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: "Invalid request format", details: error.errors },
        { status: 400 }
      );
    }

    return NextResponse.json(
      { error: error.message || "Internal server error" },
      { status: 500 }
    );
  }
}
