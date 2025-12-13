import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ClerkProvider } from "@clerk/nextjs";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "OneRing",
  description: "The only content brain you'll ever need.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body className={inter.className}>
          <header className="p-4 bg-black/50 text-white">
            <nav className="max-w-6xl mx-auto flex items-center justify-between">
              <div className="flex items-center gap-6">
                <Link href="/" className="font-bold">OneRing</Link>
                <Link href="/analytics" className="opacity-80">Analytics</Link>
                <Link href="/organizations" className="opacity-80">Organizations</Link>
              </div>
            </nav>
          </header>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}