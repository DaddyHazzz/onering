// src/app/api/referral/route.ts
import { NextRequest } from "next/server";
import { clerkClient, currentUser } from "@clerk/nextjs/server";

// Mock referral storage (in-memory)
const referrals: Record<string, string> = { "TESTCODE": "referrer-user-id" };

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    if (!userId) return Response.json({ error: 'Not authenticated' }, { status: 401 });

    const { referralCode } = await req.json();
    console.log('[referral] user', userId, 'used code', referralCode);

    const referrer = referrals[referralCode];
    if (!referrer) return Response.json({ error: 'Invalid code' }, { status: 400 });

    // award both
    const user = await clerkClient.users.getUser(userId);
    const userMeta = (user.publicMetadata || {}) as any;
    const userRing = (userMeta.ring || 0) + 100;
    await clerkClient.users.updateUserMetadata(userId, { publicMetadata: { ...userMeta, ring: userRing } });

    const refUser = await clerkClient.users.getUser(referrer);
    const refMeta = (refUser.publicMetadata || {}) as any;
    const refRing = (refMeta.ring || 0) + 100;
    await clerkClient.users.updateUserMetadata(referrer, { publicMetadata: { ...refMeta, ring: refRing } });

    console.log('[referral] awarded 100 RING to', userId, 'and', referrer);
    return Response.json({ success: true, userRing, referrer, refRing });
  } catch (err: any) {
    console.error('[referral] error:', err);
    return Response.json({ error: err?.message || String(err) }, { status: 500 });
  }
}
