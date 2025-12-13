import { NextResponse } from 'next/server';

export async function GET(req: Request) {
  console.log('[api/auth/callback/clerk] GET received; redirecting to /dashboard');
  return NextResponse.redirect(new URL('/dashboard', req.url));
}

export async function POST(req: Request) {
  console.log('[api/auth/callback/clerk] POST received');
  try {
    const body = await req.json().catch(() => ({}));
    console.log('[api/auth/callback/clerk] body:', body);
  } catch (e) {
    console.error('[api/auth/callback/clerk] parse error', e);
  }
  return NextResponse.redirect(new URL('/dashboard', req.url));
}
