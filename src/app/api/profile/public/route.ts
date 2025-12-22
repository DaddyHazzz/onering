/**
 * src/app/api/profile/public/route.ts
 * Proxy to backend GET /v1/profile/public
 * Public endpoint (no Clerk auth required)
 */

import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";

const responseSchema = z.object({
  success: z.boolean(),
  data: z.object({
    user_id: z.string(),
    handle: z.string().optional(),
    display_name: z.string(),
    streak: z.object({
      current_length: z.number(),
      longest_length: z.number(),
      status: z.enum(["active", "on_break", "building"]),
      last_active_date: z.string(),
    }),
    momentum_today: z.object({
      score: z.number(),
      trend: z.enum(["up", "flat", "down"]),
      components: z.object({
        streakComponent: z.number(),
        consistencyComponent: z.number(),
        challengeComponent: z.number(),
        coachComponent: z.number(),
      }),
      nextActionHint: z.string(),
      computedAt: z.string(),
    }),
    momentum_weekly: z.array(
      z.object({
        score: z.number(),
        trend: z.enum(["up", "flat", "down"]),
        components: z.object({
          streakComponent: z.number(),
          consistencyComponent: z.number(),
          challengeComponent: z.number(),
          coachComponent: z.number(),
        }),
        nextActionHint: z.string(),
        computedAt: z.string(),
      })
    ),
    recent_posts: z.array(
      z.object({
        id: z.string(),
        platform: z.string(),
        content: z.string(),
        created_at: z.string(),
      })
    ),
    profile_summary: z.string(),
    computed_at: z.string(),
  }),
  error: z.string().optional(),
});

export async function GET(req: NextRequest) {
  try {
    const { searchParams } = new URL(req.url);
    const handle = searchParams.get("handle");
    const userId = searchParams.get("user_id");

    if (!handle && !userId) {
      return NextResponse.json(
        {
          error: "Missing required parameter: handle or user_id",
        },
        { status: 400 }
      );
    }

    // Build backend query
    const backendUrl = new URL(
      `${process.env.BACKEND_URL || "http://localhost:8000"}/v1/profile/public`
    );
    if (handle) backendUrl.searchParams.set("handle", handle);
    if (userId) backendUrl.searchParams.set("user_id", userId);

    // Call backend
    const backendResponse = await fetch(backendUrl.toString(), {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await backendResponse.json();

    // Validate response shape
    if (!backendResponse.ok) {
      return NextResponse.json(
        {
          error: data.error || "Failed to fetch profile from backend",
        },
        { status: backendResponse.status }
      );
    }

    // Validate against schema
    const validated = responseSchema.parse(data);

    return NextResponse.json(validated, {
      status: 200,
      headers: {
        "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300",
      },
    });
  } catch (error: any) {
    console.error("[profile/public] error:", error);

    if (error instanceof z.ZodError) {
      return NextResponse.json(
        {
          error: "Invalid profile response format",
          details: error.errors,
        },
        { status: 500 }
      );
    }

    return NextResponse.json(
      {
        error: error.message || "Internal server error",
      },
      { status: 500 }
    );
  }
}
