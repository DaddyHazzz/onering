"use client";

import { SignUp } from "@clerk/nextjs";

export default function SignUpPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-black text-white">
      <div className="w-full max-w-md p-8">
        <SignUp path="/sign-up" routing="path" signInUrl="/sign-in" />
      </div>
    </main>
  );
}
import { SignUp } from "@clerk/nextjs";

export default function Page() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-black">
      <SignUp />
    </div>
  );
}