/**
 * src/app/api/collab/drafts/route.ts
 * Collaboration drafts API proxy: create and list drafts
 * POST /api/collab/drafts -> create draft with Clerk auth
 * GET /api/collab/drafts -> list user's drafts
 */

import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

const createDraftSchema = z.object({
  title: z.string().min(1).max(200),
  platform: z.enum(["x", "instagram", "tiktok", "youtube"]),
  initial_segment: z.string().max(500).optional(),
});

type CreateDraftRequest = z.infer<typeof createDraftSchema>;

export async function POST(req: NextRequest) {
  try {
    const user = await currentUser();
    if (!user) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const data = createDraftSchema.parse(body);

    // Forward to backend
    const backendRes = await fetch("http://localhost:8000/v1/collab/drafts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: data.title,
        platform: data.platform,
        initial_segment: data.initial_segment,
      }),
      searchParams: new URLSearchParams({ user_id: user.id }),
    });

    if (!backendRes.ok) {
      const error = await backendRes.json();
      return Response.json(
        { error: error.detail || "Failed to create draft" },
        { status: backendRes.status }
      );
    }

    const result = await backendRes.json();
    return Response.json(result);
  } catch (error: any) {
    console.error("[collab/drafts POST]", error.message);
    if (error instanceof z.ZodError) {
      return Response.json(
        { error: "Invalid input", details: error.errors },
        { status: 400 }
      );
    }
    return Response.json({ error: error.message }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  try {
    const user = await currentUser();
    if (!user) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Forward to backend
    const url = new URL("http://localhost:8000/v1/collab/drafts");
    url.searchParams.set("user_id", user.id);

    const backendRes = await fetch(url.toString(), {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!backendRes.ok) {
      const error = await backendRes.json();
      return Response.json(
        { error: error.detail || "Failed to list drafts" },
        { status: backendRes.status }
      );
    }

    const result = await backendRes.json();
    return Response.json(result);
  } catch (error: any) {
    console.error("[collab/drafts GET]", error.message);
    return Response.json({ error: error.message }, { status: 500 });
  }
}
