"use client";

import { useState } from "react";
import { useUser } from "@clerk/nextjs";

export default function OrgsPage() {
  const { user } = useUser();
  const [name, setName] = useState("");

  return (
    <main className="p-10 text-white">
      <h1 className="text-3xl font-bold mb-4">Organizations</h1>
      {!user && <p>Please sign in to manage organizations.</p>}

      <div className="mt-6">
        <label className="block mb-2">Create an Org</label>
        <input value={name} onChange={(e) => setName(e.target.value)} className="p-2 rounded" placeholder="Org name" />
        <button onClick={() => alert('Org creation mocked')} className="ml-3 px-4 py-2 bg-purple-600 rounded">Create</button>
      </div>
    </main>
  );
}
