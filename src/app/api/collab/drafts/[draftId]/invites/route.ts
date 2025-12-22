/**
 * src/app/api/collab/drafts/[draftId]/invites/route.ts
 * List and create invites for a collaboration draft
 */

import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";
import { createHash } from "crypto";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const CreateInviteSchema = z.object({
  target: z.string().min(1, "Target required"),
  expiresInHours: z.number().min(1).max(168).optional().default(72),
  idempotencyKey: z.string().optional(),
});

export async function GET(
  req: NextRequest,
  context: { params: { draftId: string } }
) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { draftId } = context.params;

    const backendRes = await fetch(
      `${BACKEND_URL}/v1/collab/drafts/${draftId}/invites?user_id=${userId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!backendRes.ok) {
      const text = await backendRes.text();
      // Check for HTML response (misconfigured backend)
      if (text.trim().startsWith("<")) {
        return NextResponse.json(
          {
            error:
              "Backend returned HTML instead of JSON. Check backend CORS and routes.",
          },
          { status: 502 }
        );
      }
      return NextResponse.json(
        { error: text || "Failed to list invites" },
        { status: backendRes.status }
      );
    }

    const data = await backendRes.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("[collab/invites] GET error:", error);
    return NextResponse.json(
      { error: error.message || "Internal error" },
      { status: 500 }
    );
  }
}

export async function POST(
  req: NextRequest,
  context: { params: { draftId: string } }
) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { draftId } = context.params;
    const body = await req.json();
    const input = CreateInviteSchema.parse(body);

    // Determine if target is handle or user_id
    const isUserId = input.target.startsWith("user_");
    const payload: any = {
      expires_in_hours: input.expiresInHours,
      idempotency_key:
        input.idempotencyKey ||
        createHash("sha1")
          .update(`${userId}:${draftId}:${input.target}:create_invite`)
          .digest("hex"),
    };

    if (isUserId) {
      payload.target_user_id = input.target;
    } else {
      payload.target_handle = input.target;
    }

    const backendRes = await fetch(
      `${BACKEND_URL}/v1/collab/drafts/${draftId}/invites?user_id=${userId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }
    );

    if (!backendRes.ok) {
      const text = await backendRes.text();
      if (text.trim().startsWith("<")) {
        return NextResponse.json(
          {
            error:
              "Backend returned HTML instead of JSON. Check backend CORS and routes.",
          },
          { status: 502 }
        );
      }
      return NextResponse.json(
        { error: text || "Failed to create invite" },
        { status: backendRes.status }
      );
    }

    const data = await backendRes.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("[collab/invites] POST error:", error);
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        { error: error.errors[0].message },
        { status: 400 }
      );
    }
    return NextResponse.json(
      { error: error.message || "Internal error" },
      { status: 500 }
    );
  }
}
