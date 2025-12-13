// src/app/api/viewership/route.ts
import { NextRequest } from "next/server";
import { currentUser, clerkClient } from "@clerk/nextjs/server";

export async function GET(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    if (!userId) return Response.json({ error: 'Not authenticated' }, { status: 401 });

    const user = await clerkClient.users.getUser(userId);
    const meta = (user.publicMetadata || {}) as any;
    const posts = Array.isArray(meta.posts) ? meta.posts : [];

    // Return mock views/likes per post
    const stats = posts.map((p: any) => ({ id: p.id, platform: p.platform, views: Math.floor(Math.random()*10000), likes: Math.floor(Math.random()*2000) }));
    return Response.json({ success: true, stats });
  } catch (err: any) {
    console.error('[viewership] error', err);
    return Response.json({ error: err?.message || String(err) }, { status: 500 });
  }
}
