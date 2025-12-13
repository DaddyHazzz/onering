import { currentUser, clerkClient } from '@clerk/nextjs/server';

export async function POST(req: Request) {
  const user = await currentUser();
  if (!user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401, headers: { 'content-type': 'application/json' } });
  const { name } = await req.json();
  if (!name) return new Response(JSON.stringify({ error: 'name required' }), { status: 400, headers: { 'content-type': 'application/json' } });

  try {
    const u = await clerkClient.users.getUser(user.id);
    const pm: any = (u.publicMetadata as any) || {};
    const ring = Number(pm.ring || 0);
    const price = 100;
    if (ring < price) return new Response(JSON.stringify({ error: 'insufficient RING' }), { status: 402, headers: { 'content-type': 'application/json' } });

    const leases = Array.isArray(pm.leases) ? pm.leases : [];
    leases.push({ name, leasedAt: new Date().toISOString() });
    const newMeta = { ...pm, ring: ring - price, leases };
    await clerkClient.users.updateUser(user.id, { publicMetadata: newMeta });
    console.log('[market/lease] leased name', name, 'for user', user.id);
    return new Response(JSON.stringify({ success: true, name, ring: newMeta.ring }), { status: 200, headers: { 'content-type': 'application/json' } });
  } catch (err: any) {
    console.error('[market/lease] error', err);
    return new Response(JSON.stringify({ error: 'lease failed' }), { status: 500, headers: { 'content-type': 'application/json' } });
  }
}
