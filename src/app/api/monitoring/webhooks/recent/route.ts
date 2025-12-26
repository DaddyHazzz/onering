import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const search = req.nextUrl.searchParams;
  const status = search.get("status");
  const eventType = search.get("event_type");
  const webhookId = search.get("webhook_id");
  const limit = search.get("limit") || "20";

  const query = new URLSearchParams();
  if (status) query.set("status", status);
  if (eventType) query.set("event_type", eventType);
  if (webhookId) query.set("webhook_id", webhookId);
  query.set("limit", limit);

  const backendUrl = `${BACKEND_URL}/v1/monitoring/webhooks/recent?${query.toString()}`;
  const res = await fetch(backendUrl, {
    headers: {
      Authorization: req.headers.get("authorization") || "",
      "X-Admin-Key": req.headers.get("x-admin-key") || "",
    },
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
