import { NextRequest, NextResponse } from "next/server";
import { auth } from "@clerk/nextjs/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function GET(req: NextRequest) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const url = new URL(req.url);
  const limit = url.searchParams.get("limit") || "20";
  const res = await fetch(`${BACKEND_URL}/v1/tokens/ledger/${userId}?limit=${limit}`);
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
