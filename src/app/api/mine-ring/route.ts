import { currentUser, clerkClient } from '@clerk/nextjs/server';

export async function POST(req: Request) {
  const user = await currentUser();
  if (!user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401, headers: { 'content-type': 'application/json' } });

  try {
    const body = await req.json().catch(() => ({}));
    const amount = Number(body.amount || 100);
    const u = await clerkClient.users.getUser(user.id);
    const pm: any = (u.publicMetadata as any) || {};
    const prev = Number(pm.ring || 0);
    const next = prev + amount;
    const newMeta = { ...pm, ring: next };
    await clerkClient.users.updateUser(user.id, { publicMetadata: newMeta });
    console.log('[mine-ring] user', user.id, 'mined', amount, '-> new ring', next);
    return new Response(JSON.stringify({ success: true, ring: next }), { status: 200, headers: { 'content-type': 'application/json' } });
  } catch (err: any) {
    console.error('[mine-ring] error', err);
    return new Response(JSON.stringify({ error: 'mine failed' }), { status: 500, headers: { 'content-type': 'application/json' } });
  }
}
// src/app/api/mine-ring/route.ts
import { NextRequest } from "next/server";
import { clerkClient, currentUser } from "@clerk/nextjs/server";

export async function POST(req: NextRequest) {
  try {
    const caller = await currentUser();
    const userId = caller?.id;
    console.log('[mine-ring] currentUser:', userId);
    if (!userId) return Response.json({ error: 'Not authenticated' }, { status: 401 });

    const body = await req.json();
    const amount = Number(body.amount) || 100;

    const user = await clerkClient.users.getUser(userId);
    const meta = (user.publicMetadata || {}) as any;
    const ring = (meta.ring || 0) + amount;

    await clerkClient.users.updateUserMetadata(userId, { publicMetadata: { ...meta, ring } });
    console.log('[mine-ring] added', amount, 'RING to', userId, 'new total', ring);

    return Response.json({ success: true, ring });
  } catch (err: any) {
    console.error('[mine-ring] error:', err);
    return Response.json({ error: err?.message || String(err) }, { status: 500 });
  }
}
