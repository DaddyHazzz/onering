import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";
import { z } from "zod";

// Validate response schema
const momentumComponentsSchema = z.object({
  streakComponent: z.number().min(0).max(25),
  consistencyComponent: z.number().min(0).max(10),
  challengeComponent: z.number().min(0).max(15),
  coachComponent: z.number().min(0).max(10),
});

const momentumSnapshotSchema = z.object({
  userId: z.string(),
  date: z.string(),
  score: z.number().min(0).max(100),
  trend: z.enum(["up", "flat", "down"]),
  components: momentumComponentsSchema,
  nextActionHint: z.string(),
  computedAt: z.string(),
});

export async function GET(req: NextRequest) {
  try {
    const caller = await currentUser();
    if (!caller?.id) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    // Call backend /weekly endpoint
    const backendUrl = `http://localhost:8000/v1/momentum/weekly?user_id=${encodeURIComponent(caller.id)}`;
    const res = await fetch(backendUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    if (!res.ok) {
      const error = await res.text();
      console.error(`[momentum/weekly] backend error: ${res.status} ${error}`);
      return Response.json(
        { error: `Backend error: ${error}` },
        { status: res.status }
      );
    }

    const json = await res.json();

    // Validate response (array of snapshots)
    const snapshots = z.array(momentumSnapshotSchema).parse(json.data);
    return Response.json({ data: snapshots });
  } catch (error: any) {
    console.error("[momentum/weekly] error:", error);
    return Response.json(
      { error: error.message || "Internal server error" },
      { status: 500 }
    );
  }
}
