import { currentUser, clerkClient } from '@clerk/nextjs/server';
import { prisma } from '@/lib/db';
import { applyLedgerSpend, buildIdempotencyKey, getEffectiveRingBalance, getTokenIssuanceMode } from '@/lib/ring-ledger';

export async function POST(req: Request) {
  const user = await currentUser();
  if (!user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401, headers: { 'content-type': 'application/json' } });
  const { name } = await req.json();
  if (!name) return new Response(JSON.stringify({ error: 'name required' }), { status: 400, headers: { 'content-type': 'application/json' } });

  try {
    const u = await clerkClient.users.getUser(user.id);
    const pm: any = (u.publicMetadata as any) || {};
    const tokenMode = getTokenIssuanceMode();
    await prisma.user.upsert({
      where: { clerkId: user.id },
      update: {},
      create: { clerkId: user.id },
    });
    const price = 100;
    if (tokenMode === "off") {
      const ring = Number(pm.ring || 0);
      if (ring < price) return new Response(JSON.stringify({ error: 'insufficient RING' }), { status: 402, headers: { 'content-type': 'application/json' } });
    } else {
      const spend = await applyLedgerSpend({
        userId: user.id,
        amount: price,
        reasonCode: "market_lease",
        metadata: { name },
        idempotencyKey: buildIdempotencyKey([user.id, "market_lease", name]),
      });
      if (!spend.ok) {
        return new Response(JSON.stringify({ error: 'insufficient RING', code: spend.error || 'LEGACY_RING_WRITE_BLOCKED' }), { status: 402, headers: { 'content-type': 'application/json' } });
      }
    }

    const leases = Array.isArray(pm.leases) ? pm.leases : [];
    leases.push({ name, leasedAt: new Date().toISOString() });

    const newMeta = tokenMode === "off"
      ? { ...pm, ring: Number(pm.ring || 0) - price, leases }
      : { ...pm, leases };
    await clerkClient.users.updateUser(user.id, { publicMetadata: newMeta });
    console.log('[market/lease] leased name', name, 'for user', user.id);
    const summary = await getEffectiveRingBalance(user.id);
    return new Response(JSON.stringify({ success: true, name, ring: summary.effectiveBalance }), { status: 200, headers: { 'content-type': 'application/json' } });
  } catch (err: any) {
    console.error('[market/lease] error', err);
    return new Response(JSON.stringify({ error: 'lease failed' }), { status: 500, headers: { 'content-type': 'application/json' } });
  }
}
