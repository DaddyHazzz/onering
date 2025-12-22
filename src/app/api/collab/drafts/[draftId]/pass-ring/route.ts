/**
 * src/app/api/collab/drafts/[draftId]/pass-ring/route.ts
 * Pass ring to another user (idempotent)
 */

import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

const passRingSchema = z.object({
  to_user_id: z.string(),
  idempotency_key: z.string().uuid(),
});

type PassRingRequest = z.infer<typeof passRingSchema>;

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ draftId: string }> }
) {
  try {
    const user = await currentUser();
    if (!user) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    const body = await req.json();
    const data = passRingSchema.parse(body);

    const { draftId } = await params;

    // Forward to backend
    const url = new URL(
      `http://localhost:8000/v1/collab/drafts/${draftId}/pass-ring`
    );
    url.searchParams.set("user_id", user.id);

    const backendRes = await fetch(url.toString(), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        to_user_id: data.to_user_id,
        idempotency_key: data.idempotency_key,
      }),
    });

    if (!backendRes.ok) {
      const error = await backendRes.json();
      return Response.json(
        { error: error.detail || "Failed to pass ring" },
        { status: backendRes.status }
      );
    }

    const result = await backendRes.json();
    return Response.json(result);
  } catch (error: any) {
    console.error("[collab/pass-ring POST]", error.message);
    if (error instanceof z.ZodError) {
      return Response.json(
        { error: "Invalid input", details: error.errors },
        { status: 400 }
      );
    }
    return Response.json({ error: error.message }, { status: 500 });
  }
}
