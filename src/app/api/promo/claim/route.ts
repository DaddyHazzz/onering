import { currentUser, clerkClient } from '@clerk/nextjs/server';

const PROMOS: Record<string, number> = {
  FIRST100: 1000,
  FELONFOUNDER: 500,
};

export async function POST(req: Request) {
  const user = await currentUser();
  if (!user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401, headers: { 'content-type': 'application/json' } });
  const { code } = await req.json();
  if (!code) return new Response(JSON.stringify({ error: 'code required' }), { status: 400, headers: { 'content-type': 'application/json' } });

  const key = String(code || '').toUpperCase();
  const amount = PROMOS[key];
  if (!amount) return new Response(JSON.stringify({ error: 'invalid promo' }), { status: 404, headers: { 'content-type': 'application/json' } });

  try {
    const userRec = await clerkClient.users.getUser(user.id);
    const pm: any = (userRec.publicMetadata as any) || {};
    const claimed: string[] = Array.isArray(pm.claimedPromos) ? pm.claimedPromos : [];
    if (claimed.includes(key)) return new Response(JSON.stringify({ error: 'promo already claimed' }), { status: 400, headers: { 'content-type': 'application/json' } });

    const prev = Number(pm.ring || 0);
    const next = prev + amount;
    claimed.push(key);
    const newMeta = { ...pm, ring: next, claimedPromos: claimed };
    await clerkClient.users.updateUser(user.id, { publicMetadata: newMeta });
    console.log('[promo/claim] user claimed promo', user.id, key, amount);
    return new Response(JSON.stringify({ success: true, amount, ring: next }), { status: 200, headers: { 'content-type': 'application/json' } });
  } catch (err: any) {
    console.error('[promo/claim] error', err);
    return new Response(JSON.stringify({ error: 'claim failed' }), { status: 500, headers: { 'content-type': 'application/json' } });
  }
}
