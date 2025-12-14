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

    // clerkClient() is a function in newer Clerk SDK
    const clerk = await clerkClient();
    const user = await clerk.users.getUser(userId);
    const meta = (user.publicMetadata || {}) as any;
    const ring = (meta.ring || 0) + amount;

    await clerk.users.updateUser(userId, { publicMetadata: { ...meta, ring } });
    console.log('[mine-ring] added', amount, 'RING to', userId, 'new total', ring);

    return Response.json({ success: true, ring });
  } catch (err: any) {
    console.error('[mine-ring] error:', err);
    return Response.json({ error: err?.message || String(err) }, { status: 500 });
  }
}
