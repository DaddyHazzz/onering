"use client";

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

export default function SSOCallbackPage() {
  const router = useRouter();
  useEffect(() => {
    router.replace('/dashboard');
  }, [router]);

  return (
    <main className="flex min-h-screen items-center justify-center bg-black text-white">
      <div className="text-center">
        <h2 className="text-2xl font-bold mb-2">Signing you in…</h2>
        <p className="opacity-70">If you are not redirected, <a className="underline" href="/dashboard">click here</a>.</p>
      </div>
    </main>
  );
}
