import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-black text-white">
      <h1 className="mb-4 text-center text-6xl font-black tracking-tighter md:text-8xl">
        OneRing
      </h1>
      <p className="mb-12 text-center text-2xl opacity-80">
        The only AI content brain you’ll ever need.
      </p>

      <div className="flex gap-6">
        <Link
          href="/sign-up"
          className="rounded-full bg-purple-600 px-10 py-5 text-2xl font-bold transition hover:bg-purple-500"
        >
          Start for free
        </Link>
        <Link
          href="/sign-in"
          className="rounded-full border-2 border-white px-10 py-5 text-2xl font-bold transition hover:bg-white hover:text-black"
        >
          Sign in
        </Link>
      </div>

      <p className="absolute bottom-8 text-sm opacity-50">
        Built by a felon in a sober living house with nothing but a laptop and Grok.
      </p>
    </main>
  );
}