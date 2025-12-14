"use client";

import { SignIn } from "@clerk/nextjs";

export default function SignInPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-black text-white">
      <div className="w-full max-w-md p-8">
        <SignIn path="/sign-in" routing="path" signUpUrl="/sign-up" />
      </div>
    </main>
  );
}
