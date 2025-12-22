/**
 * src/app/api/collab/invites/[inviteId]/revoke/route.ts
 * Revoke a collaboration invite
 */

import { NextRequest, NextResponse } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";
import { createHash } from "crypto";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const RevokeInviteSchema = z.object({
  draftId: z.string().min(1, "Draft ID required"),
  idempotencyKey: z.string().optional(),
});

export async function POST(
  req: NextRequest,
  context: { params: { inviteId: string } }
) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    if (!userId) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { inviteId } = context.params;
    const body = await req.json();
    const input = RevokeInviteSchema.parse(body);

    const payload = {
      idempotency_key:
        input.idempotencyKey ||
        createHash("sha1")
          .update(`${userId}:${inviteId}:${input.draftId}:revoke_invite`)
          .digest("hex"),
    };

    const backendRes = await fetch(
      `${BACKEND_URL}/v1/collab/invites/${inviteId}/revoke?user_id=${userId}`,
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
        { error: text || "Failed to revoke invite" },
        { status: backendRes.status }
      );
    }

    const data = await backendRes.json();
    return NextResponse.json(data);
  } catch (error: any) {
    console.error("[collab/invites/revoke] POST error:", error);
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
