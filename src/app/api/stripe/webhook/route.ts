// src/app/api/stripe/webhook/route.ts
import Stripe from "stripe";
import { clerkClient } from "@clerk/nextjs/server";
import { prisma } from "@/lib/db";
import { applyLedgerEarn, buildIdempotencyKey, ensureLegacyRingWritesAllowed, getTokenIssuanceMode } from "@/lib/ring-ledger";

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
      const clerkId = session.client_reference_id;
      console.log('[stripe/webhook] checkout.session.completed for clerk user:', clerkId);

      if (clerkId) {
        try {
          // Upsert user in Postgres via Prisma
          const tokenMode = getTokenIssuanceMode();
          const ringAward = 500;
          if (tokenMode === "off") {
            ensureLegacyRingWritesAllowed();
          }
          const user = await prisma.user.upsert({
            where: { clerkId },
            update: {
              verified: true,
              ...(tokenMode === "off" ? { ringBalance: { increment: ringAward } } : {}),
            },
            create: {
              clerkId,
              verified: true,
              ringBalance: tokenMode === "off" ? ringAward : 0,
            },
          });

          if (tokenMode !== "off") {
            const earned = await applyLedgerEarn({
              userId: clerkId,
              amount: ringAward,
              reasonCode: "stripe_credit",
              metadata: { event_id: event.id },
              idempotencyKey: buildIdempotencyKey([clerkId, "stripe_credit", event.id]),
            });
            if (!earned.ok) {
              console.warn("[stripe/webhook] ledger earn blocked:", earned.error);
            }
          }

          console.log('[stripe/webhook] upserted user to DB:', user.id, { ringBalance: user.ringBalance, verified: user.verified });

          // Also update Clerk metadata for fallback/sync (legacy only)
          if (tokenMode === "off") {
            try {
              const client: any = typeof clerkClient === 'function' ? await clerkClient() : clerkClient;
              const clerkUser = await client.users.getUser(clerkId);
              const pm: any = (clerkUser?.publicMetadata as any) || {};
              const processed: string[] = Array.isArray(pm.processedStripeEvents) ? pm.processedStripeEvents : [];

              const newMeta = {
                ...pm,
                verified: true,
                subscription: 'active',
                ring: user.ringBalance,
                processedStripeEvents: [...processed, event.id]
              };
              await client.users.updateUser(clerkId, { publicMetadata: newMeta });
              console.log('[stripe/webhook] synced Clerk metadata for', clerkId);
            } catch (clerkErr: any) {
              console.warn('[stripe/webhook] failed to sync Clerk metadata:', clerkErr.message);
            }
          }
        } catch (dbErr: any) {
          console.error('[stripe/webhook] database error while upserting user:', dbErr);
        }
      }
    }

    return new Response(JSON.stringify({ received: true }), { status: 200, headers: { 'content-type': 'application/json' } });
  } catch (err: any) {
    console.error('[stripe/webhook] signature/processing error:', err?.message || err);
    return new Response(JSON.stringify({ error: err?.message || String(err) }), { status: 400, headers: { 'content-type': 'application/json' } });
  }
}
