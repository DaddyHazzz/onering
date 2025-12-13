// src/app/api/stripe/checkout/route.ts
import { NextRequest } from "next/server";
import Stripe from "stripe";
import { currentUser } from "@clerk/nextjs/server";

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, {
  apiVersion: "2022-11-15",
});

export async function GET(req: Request) {
  try {
    // Resolve the caller from Clerk session (server-side)
    const user = await currentUser();
    if (!user) return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401, headers: { 'content-type': 'application/json' } });
    const userId = user.id;

    console.log("[stripe/checkout] currentUser id:", userId);

    if (!userId) {
      return Response.json({ error: "Not authenticated" }, { status: 401 });
    }

    // Build origin-aware URLs. Prefer forwarded headers (ngrok), fall back to host.
    const proto = (req.headers.get('x-forwarded-proto') || req.headers.get('x-forwarded-protocol') || req.headers.get('forwarded-proto') || 'http');
    const host = req.headers.get('x-forwarded-host') || req.headers.get('host') || 'localhost:3000';
    const origin = `${proto}://${host}`;
    console.log('[stripe/checkout] derived origin from headers:', { proto, host, origin });

    const session = await stripe.checkout.sessions.create({
      mode: "subscription",
      payment_method_types: ["card"],
      line_items: [
        {
          price: process.env.STRIPE_PRICE_ID!,
          quantity: 1,
        },
      ],
      success_url: `${origin}/dashboard?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: `${origin}/dashboard`,
      client_reference_id: userId,
    });

    console.log("[stripe/checkout] session created:", session.id, session.url);

    return Response.json({ sessionUrl: session.url });
  } catch (err: any) {
    console.error("[stripe/checkout] error:", err);
    return Response.json({ error: err?.message || String(err) }, { status: 500 });
  }
}
