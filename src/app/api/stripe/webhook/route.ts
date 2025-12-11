// src/app/api/stripe/webhook/route.ts
import { NextRequest } from "next/server";
import Stripe from "stripe";
import { headers } from "next/headers";
import { currentUser, clerkClient } from "@clerk/nextjs/server";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: "2025-11-01" });
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET!;

export async function POST(req: NextRequest) {
  const sig = headers().get("stripe-signature")!;
  const body = await req.text();

  try {
    const event = stripe.webhooks.constructEvent(body, sig, webhookSecret);

    if (event.type === "checkout.session.completed") {
      const session = event.data.object as Stripe.Checkout.Session;
      const userId = session.client_reference_id; // We'll set this in checkout
      await clerkClient.users.updateUserMetadata(userId!, {
        publicMetadata: { verified: true, subscription: "active" },
      });
    }

    return Response.json({ received: true });
  } catch (err: any) {
    return Response.json({ error: err.message }, { status: 400 });
  }
}