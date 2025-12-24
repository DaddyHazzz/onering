/**
 * Hook to manage Clerk JWT token in localStorage.
 * 
 * Phase 6.1: Stores Clerk JWT for API requests.
 * Called from client components that need auth.
 */

"use client";

import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";

/**
 * Sync Clerk JWT to localStorage whenever auth state changes.
 * 
 * This allows apiFetch() to access the token without needing
 * to pass useAuth through the entire component tree.
 */
export function useClerkToken() {
  const { getToken } = useAuth();

  useEffect(() => {
    const syncToken = async () => {
      try {
        const token = await getToken();
        if (token) {
          localStorage.setItem("clerk_token", token);
        } else {
          localStorage.removeItem("clerk_token");
        }
      } catch (error) {
        console.error("Failed to sync Clerk token:", error);
        localStorage.removeItem("clerk_token");
      }
    };

    syncToken();

    // Sync whenever tab becomes active (in case token expired)
    const interval = setInterval(syncToken, 60000); // Every minute

    return () => clearInterval(interval);
  }, [getToken]);
}
