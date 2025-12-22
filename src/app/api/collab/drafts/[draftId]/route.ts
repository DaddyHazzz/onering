/**
 * src/app/api/collab/drafts/[draftId]/route.ts
 * Get draft by ID
 */

import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ draftId: string }> }
) {
  try {
    const user = await currentUser();
    if (!user) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    const { draftId } = await params;

    // Forward to backend
    const backendRes = await fetch(
      `http://localhost:8000/v1/collab/drafts/${draftId}`,
      {
        method: "GET",
        headers: { "Content-Type": "application/json" },
      }
    );

    if (!backendRes.ok) {
      const error = await backendRes.json();
      return Response.json(
        { error: error.detail || "Draft not found" },
        { status: backendRes.status }
      );
    }

    const result = await backendRes.json();
    return Response.json(result);
  } catch (error: any) {
    console.error("[collab/drafts/[id] GET]", error.message);
    return Response.json({ error: error.message }, { status: 500 });
  }
}
