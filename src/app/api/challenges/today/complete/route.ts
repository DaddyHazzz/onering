import { currentUser } from "@clerk/nextjs/server";
import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  const caller = await currentUser();
  const userId = caller?.id;

  if (!userId) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json();
  const { challenge_id, completion_source } = body;

  if (!challenge_id) {
    return Response.json({ error: "challenge_id required" }, { status: 400 });
  }

  const res = await fetch(`${BACKEND_URL}/v1/challenges/today/complete`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_id: userId,
      challenge_id,
      completion_source: completion_source || null,
    }),
  });

  const data = await res.json().catch(() => ({ error: "Unable to parse response" }));

  if (!res.ok) {
    return Response.json({ error: data?.error || "Failed to complete challenge" }, { status: res.status });
  }

  return Response.json(data);
}
