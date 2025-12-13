import { currentUser, clerkClient } from '@clerk/nextjs/server';

export async function POST(req: Request) {
  const user = await currentUser();
  if (!user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401, headers: { 'content-type': 'application/json' } });
  const body = await req.json();
  const code = (body.code || '').toString().toUpperCase();
  if (!code) return new Response(JSON.stringify({ error: 'code required' }), { status: 400, headers: { 'content-type': 'application/json' } });

  try {
    // Find referrer by scanning users for publicMetadata.referralCode
    const list = await clerkClient.users.getUserList({ limit: 100 });
    const ref = list.find((u: any) => ((u.publicMetadata || {}) as any).referralCode === code);
    if (!ref) return new Response(JSON.stringify({ error: 'invalid code' }), { status: 404, headers: { 'content-type': 'application/json' } });

    const referrerId = ref.id;
    if (referrerId === user.id) return new Response(JSON.stringify({ error: 'cannot claim your own code' }), { status: 400, headers: { 'content-type': 'application/json' } });

    // Check claimant hasn't claimed before
    const claimant = await clerkClient.users.getUser(user.id);
    const claimantMeta: any = (claimant.publicMetadata as any) || {};
    if (claimantMeta.referredBy) return new Response(JSON.stringify({ error: 'already claimed' }), { status: 400, headers: { 'content-type': 'application/json' } });

    // Award 200 RING to both
    const refMeta: any = (ref.publicMetadata as any) || {};
    const refPrev = Number(refMeta.ring || 0);
    const claimantPrev = Number(claimantMeta.ring || 0);

    const refNew = refPrev + 200;
    const claimantNew = claimantPrev + 200;

    await clerkClient.users.updateUser(referrerId, { publicMetadata: { ...refMeta, ring: refNew } });
    await clerkClient.users.updateUser(user.id, { publicMetadata: { ...claimantMeta, ring: claimantNew, referredBy: referrerId } });

    console.log('[referral/claim] awarded 200 RING to', referrerId, 'and', user.id);
    return new Response(JSON.stringify({ success: true, referrerId, claimantNew, refNew }), { status: 200, headers: { 'content-type': 'application/json' } });
  } catch (err: any) {
    console.error('[referral/claim] error', err);
    return new Response(JSON.stringify({ error: 'claim failed' }), { status: 500, headers: { 'content-type': 'application/json' } });
  }
}
