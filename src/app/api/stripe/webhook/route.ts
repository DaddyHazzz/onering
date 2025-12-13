// src/app/api/stripe/webhook/route.ts
import { NextRequest } from "next/server";
import Stripe from "stripe";
import { headers } from "next/headers";
import { clerkClient } from "@clerk/nextjs/server";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: "2022-11-15" });
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!;

export async function POST(req: NextRequest) {
  // Read raw body for signature verification
  const sig = headers().get("stripe-signature");
  const buf = await req.arrayBuffer();
  const rawBody = Buffer.from(buf);

  console.log("[stripe/webhook] received request, sig present:", Boolean(sig));

  try {
    const event = stripe.webhooks.constructEvent(rawBody, sig || "", webhookSecret);

    console.log("[stripe/webhook] event type:", event.type);

    if (event.type === "checkout.session.completed") {
      const session = event.data.object as Stripe.Checkout.Session;
      const userId = session.client_reference_id;
      console.log("[stripe/webhook] checkout.session.completed for user:", userId);

      if (userId) {
        try {
          const user = await clerkClient.users.getUser(userId);
          const pm: any = (user?.publicMetadata as any) || {};
          const prevRing = Number(pm.ring || 0);
          const newRing = prevRing + 500;
          const newMeta = { ...pm, verified: true, subscription: "active", ring: newRing };
          await clerkClient.users.updateUser(userId, { publicMetadata: newMeta });
          console.log("[stripe/webhook] updated Clerk metadata for user:", userId, newMeta);
        } catch (uErr: any) {
          console.error("[stripe/webhook] clerk update error:", uErr);
        }
      }
    }

    return Response.json({ received: true });
  } catch (err: any) {
    console.error("[stripe/webhook] signature/processing error:", err?.message || err);
    return Response.json({ error: err?.message || String(err) }, { status: 400 });
  }
}