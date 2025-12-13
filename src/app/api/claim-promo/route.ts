// src/app/api/claim-promo/route.ts
import { NextRequest } from "next/server";
import { currentUser, clerkClient } from "@clerk/nextjs/server";

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    if (!userId) return Response.json({ error: 'Not authenticated' }, { status: 401 });

    const { code } = await req.json();
    console.log('[claim-promo] user', userId, 'claims', code);

    // Mock promo: POST5 gives 500 RING if user has >=5 posts
    const user = await clerkClient.users.getUser(userId);
    const meta = (user.publicMetadata || {}) as any;
    const posts = Array.isArray(meta.posts) ? meta.posts : [];

    if (code === 'POST5' && posts.length >= 5) {
      const ring = (meta.ring || 0) + 500;
      await clerkClient.users.updateUserMetadata(userId, { publicMetadata: { ...meta, ring } });
      return Response.json({ success: true, ring });
    }

    return Response.json({ error: 'Promo conditions not met' }, { status: 400 });
  } catch (err: any) {
    console.error('[claim-promo] error:', err);
    return Response.json({ error: err?.message || String(err) }, { status: 500 });
  }
}
