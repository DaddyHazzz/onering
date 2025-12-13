// src/proxy.ts
import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

// Initialize Clerk middleware
const mw = clerkMiddleware();

// Public paths that should not be intercepted by auth middleware
const PUBLIC_PATHS = [
  "/",
  "/sign-in",
  "/sign-up",
    "/sign-in/sso-callback",
    "/api/stripe/webhook",
  "/_next",
  "/favicon.ico",
];

export default function proxy(req: Request, ev: any) {
  try {
    const url = new URL(req.url);
    const pathname = url.pathname;
    console.log("[proxy] incoming request:", req.method, pathname);

    // Allow public paths to pass through without Clerk protecting them
    if (PUBLIC_PATHS.some((p) => pathname === p || pathname.startsWith(p + "/"))) {
      console.log("[proxy] public path, skipping Clerk middleware:", pathname);
      return NextResponse.next();
    }

    // Protect dashboard and API routes via Clerk middleware
    if (pathname.startsWith("/dashboard") || pathname.startsWith("/api")) {
      console.log("[proxy] protected path, invoking Clerk middleware:", pathname);
      return mw(req as any, ev);
    }

    // Default: don't interfere
    return NextResponse.next();
  } catch (err) {
    console.error('[proxy] error handling middleware', err);
    return NextResponse.next();
  }
}

export const config = { matcher: ["/dashboard", "/api/:path*"] };
