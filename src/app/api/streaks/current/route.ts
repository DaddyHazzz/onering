import { currentUser } from "@clerk/nextjs/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET() {
  const caller = await currentUser();
  const userId = caller?.id;

  if (!userId) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }

  const res = await fetch(
    `${BACKEND_URL}/v1/streaks/current?user_id=${encodeURIComponent(userId)}`,
    { cache: "no-store" }
  );

  const data = await res.json().catch(() => ({ error: "Unable to parse response" }));

  if (!res.ok) {
    return Response.json({ error: data?.error || "Failed to load streak" }, { status: res.status });
  }

  return Response.json(data);
}
