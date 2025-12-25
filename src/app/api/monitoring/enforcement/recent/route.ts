import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const limit = url.searchParams.get("limit") || "50";
  const since = url.searchParams.get("since");

  const backendUrl = new URL(`${BACKEND_URL}/v1/monitoring/enforcement/recent`);
  backendUrl.searchParams.set("limit", limit);
  if (since) backendUrl.searchParams.set("since", since);

  const res = await fetch(backendUrl.toString(), {
    headers: {
      Authorization: req.headers.get("authorization") || "",
      "X-Admin-Key": req.headers.get("x-admin-key") || "",
    },
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
