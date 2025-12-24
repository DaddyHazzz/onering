/**
 * Client component that syncs Clerk JWT to localStorage.
 * 
 * Wrapped by RootLayout so all pages have access to Clerk token.
 */

"use client";

import { useClerkToken } from "@/hooks/useClerkToken";
import { ReactNode } from "react";

export function ClerkTokenSync({ children }: { children: ReactNode }) {
  useClerkToken();
  return children;
}
