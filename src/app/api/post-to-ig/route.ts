// src/app/api/post-to-ig/route.ts
import { NextRequest } from "next/server";
import { currentUser } from "@clerk/nextjs/server";

// Simple rate limiter map shared with post-to-x (separate map for IG)
const igRate = new Map<string, { count: number; windowStart: number }>();
const IG_WINDOW_MS = 60 * 1000;
const IG_MAX = 3;

function igCheck(userId: string) {
  const now = Date.now();
  const e = igRate.get(userId);
  if (!e) {
    igRate.set(userId, { count: 1, windowStart: now });
    return true;
  }
  if (now - e.windowStart > IG_WINDOW_MS) {
    igRate.set(userId, { count: 1, windowStart: now });
    return true;
  }
  if (e.count >= IG_MAX) return false;
  e.count += 1;
  return true;
}

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    console.log("[post-to-ig] currentUser:", userId);
    if (!userId) return Response.json({ error: "Not authenticated" }, { status: 401 });
    if (!igCheck(userId)) return Response.json({ error: "Rate limit" }, { status: 429 });

    const body = await req.json();
    const content = String(body.content || "");

    const token = process.env.META_ACCESS_TOKEN;
    const pageId = process.env.META_PAGE_ID;

    if (!token || !pageId) {
      console.warn("[post-to-ig] META_ACCESS_TOKEN or META_PAGE_ID not set");
      return Response.json({ error: "Meta credentials not configured" }, { status: 500 });
    }

    // Pages API: publish message
    const res = await fetch(`https://graph.facebook.com/${pageId}/feed`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ message: content, access_token: token }),
    });

    const data = await res.json();
    console.log("[post-to-ig] response:", data);
    if (!res.ok) return Response.json({ error: data }, { status: 500 });

    return Response.json({ success: true, id: data.id });
  } catch (err: any) {
    console.error("[post-to-ig] error:", err);
    return Response.json({ error: err?.message || String(err) }, { status: 500 });
  }
}
