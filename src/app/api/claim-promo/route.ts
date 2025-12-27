// src/app/api/claim-promo/route.ts
import { NextRequest } from "next/server";
import { currentUser, clerkClient } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { applyLedgerEarn, getTokenIssuanceMode } from "@/lib/ring-ledger";

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
      const tokenMode = getTokenIssuanceMode();
      const award = 500;
      await prisma.user.upsert({
        where: { clerkId: userId },
        update: {},
        create: { clerkId: userId },
      });

      if (tokenMode === "off") {
        const ring = (meta.ring || 0) + award;
        await clerkClient.users.updateUserMetadata(userId, { publicMetadata: { ...meta, ring } });
        return Response.json({ success: true, ring });
      }

      const earned = await applyLedgerEarn({
        userId,
        amount: award,
        reasonCode: "promo_post5",
        metadata: { post_count: posts.length },
      });
      if (!earned.ok) {
        return Response.json({ error: "Promo blocked", code: earned.error || "LEGACY_RING_WRITE_BLOCKED" }, { status: 400 });
      }
      return Response.json({ success: true, ring: award });
    }

    return Response.json({ error: 'Promo conditions not met' }, { status: 400 });
  } catch (err: any) {
    console.error('[claim-promo] error:', err);
    return Response.json({ error: err?.message || String(err) }, { status: 500 });
  }
}
