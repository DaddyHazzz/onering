/**
 * src/app/api/profile/share-card/route.ts
 * Proxy to backend share card endpoint with Clerk auth.
 */

import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

const ShareCardSchema = z.object({
  title: z.string(),
  subtitle: z.string(),
  metrics: z.object({
    streak: z.number().min(0),
    momentum_score: z.number().min(0).max(100),
    weekly_delta: z.number().min(-100).max(100),
    top_platform: z.string(),
  }),
  tagline: z.string(),
  theme: z.object({
    bg: z.string(),
    accent: z.string(),
  }),
  generated_at: z.string().datetime(),
});

export async function GET(req: NextRequest) {
  try {
    const caller = await currentUser();
    if (!caller?.id) {
      return Response.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const handle = req.nextUrl.searchParams.get("handle") || "";
    const style = req.nextUrl.searchParams.get("style") || "default";

    if (!handle.trim()) {
      return Response.json(
        { error: "handle required" },
        { status: 400 }
      );
    }

    // Call backend
    const backendUrl = new URL(
      `${process.env.BACKEND_URL || "http://localhost:8000"}/v1/profile/share-card`
    );
    backendUrl.searchParams.set("handle", handle);
    backendUrl.searchParams.set("style", style);

    const backendRes = await fetch(backendUrl.toString(), {
      method: "GET",
      cache: "no-store",
    });

    if (!backendRes.ok) {
      const err = await backendRes.text();
      console.error("[share-card] backend error:", err);
      return Response.json(
        { error: "Failed to generate share card" },
        { status: backendRes.status }
      );
    }

    const data = await backendRes.json();

    // Validate response structure
    const validated = ShareCardSchema.parse(data);

    return Response.json({ data: validated }, { status: 200 });
  } catch (error: any) {
    console.error("[share-card] error:", error);
    return Response.json(
      { error: error.message || "Internal error" },
      { status: 500 }
    );
  }
}
