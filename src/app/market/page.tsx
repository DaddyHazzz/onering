"use client";

import { useState } from "react";

export default function MarketPage() {
  const [items] = useState([
    { name: 'badass@onering', price: 100 },
    { name: 'kingpin@onering', price: 100 },
    { name: 'felonator@onering', price: 100 },
  ]);
  const [loading, setLoading] = useState<string | null>(null);

  async function lease(name: string) {
    setLoading(name);
    try {
      const res = await fetch('/api/market/lease', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ name }) });
      const d = await res.json();
      if (!res.ok) return alert(d.error || 'lease failed');
      alert(`Leased ${d.name}. Remaining RING: ${d.ring}`);
    } catch (e) {
      console.error('lease error', e);
      alert('lease failed');
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="p-10 text-white">
      <h1 className="text-3xl font-bold mb-6">Name Marketplace (mock)</h1>
      <table className="w-full">
        <thead><tr className="border-b border-white/10"><th>Name</th><th>Price</th><th></th></tr></thead>
        <tbody>
          {items.map(i => (
            <tr key={i.name} className="border-b border-white/5">
              <td>{i.name}</td>
              <td>{i.price} RING</td>
              <td>
                <button disabled={!!loading} onClick={() => lease(i.name)} className="px-3 py-1 bg-purple-600 rounded">
                  {loading === i.name ? 'Leasing...' : 'Lease (100 RING)'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
