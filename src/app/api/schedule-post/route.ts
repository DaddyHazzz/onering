// src/app/api/schedule-post/route.ts
import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const { content, delayMinutes } = await req.json();
    const minutes = Number(delayMinutes) || 1;

    console.log("[schedule-post] scheduling post in minutes:", minutes);

    // Mock queue using setTimeout (dev-only, ephemeral)
    setTimeout(() => {
      console.log(`[schedule-post] executing scheduled post now. content len=${String(content)?.length}`);
      // In real app, push to Redis/Temporal. Here we just log.
    }, minutes * 60 * 1000);

    return Response.json({ scheduled: true, inMinutes: minutes });
  } catch (err: any) {
    console.error("[schedule-post] error:", err);
    return Response.json({ error: err?.message || String(err) }, { status: 500 });
  }
}
