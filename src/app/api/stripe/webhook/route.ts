// src/app/api/stripe/webhook/route.ts
import Stripe from "stripe";
import { clerkClient } from "@clerk/nextjs/server";

// Some @types may narrow allowed apiVersion literals; cast to `any` to avoid
// a type-level mismatch while still passing the desired string at runtime.
const stripe = new Stripe(process.env.STRIPE_SECRET_KEY || "", { apiVersion: "2022-11-15" as any });
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET || '';

export async function POST(req: Request) {
  // Read raw body for signature verification
  const sig = req.headers.get('stripe-signature') || '';
  const buf = await req.arrayBuffer();
  const rawBody = Buffer.from(buf);

  console.log('[stripe/webhook] received request, sig present:', Boolean(sig));

  try {
    const event = stripe.webhooks.constructEvent(rawBody, sig, webhookSecret);

    console.log('[stripe/webhook] event type:', event.type);

    if (event.type === 'checkout.session.completed') {
      const session = event.data.object as Stripe.Checkout.Session;
      const userId = session.client_reference_id;
      console.log('[stripe/webhook] checkout.session.completed for user:', userId);

      if (userId) {
        try {
          // `clerkClient` may be a function in some runtime typings; call it
          // if necessary and use the returned client object.
          const client: any = typeof clerkClient === 'function' ? await clerkClient() : clerkClient;
          const user = await client.users.getUser(userId);
          const pm: any = (user?.publicMetadata as any) || {};
          const prevRing = Number(pm.ring || 0);
          const newRing = prevRing + 500;
          const newMeta = { ...pm, verified: true, subscription: 'active', ring: newRing };
          await client.users.updateUser(userId, { publicMetadata: newMeta });
          console.log('[stripe/webhook] updated Clerk metadata for user:', userId, newMeta);
        } catch (uErr: any) {
          console.error('[stripe/webhook] clerk update error:', uErr);
        }
      }
    }

    return new Response(JSON.stringify({ received: true }), { status: 200, headers: { 'content-type': 'application/json' } });
  } catch (err: any) {
    console.error('[stripe/webhook] signature/processing error:', err?.message || err);
    return new Response(JSON.stringify({ error: err?.message || String(err) }), { status: 400, headers: { 'content-type': 'application/json' } });
  }
}