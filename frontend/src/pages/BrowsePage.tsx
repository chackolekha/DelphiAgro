import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { Listing } from "../types";

export default function BrowsePage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [filters, setFilters] = useState({ q: "", category: "", district: "", price_max: "" });

  const load = async () => {
    const params = new URLSearchParams();
    if (filters.q) params.set("q", filters.q);
    if (filters.category) params.set("category", filters.category);
    if (filters.district) params.set("district", filters.district);
    if (filters.price_max) params.set("price_max", filters.price_max);
    setListings(await api.get<Listing[]>(`/listings?${params}`));
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Browse produce</h2>
      <div className="flex flex-wrap gap-2 mb-4">
        <input
          className="border rounded px-3 py-2 flex-1 min-w-40"
          placeholder="Search…"
          value={filters.q}
          onChange={(e) => setFilters({ ...filters, q: e.target.value })}
        />
        <input
          className="border rounded px-3 py-2 w-36"
          placeholder="Category"
          value={filters.category}
          onChange={(e) => setFilters({ ...filters, category: e.target.value })}
        />
        <input
          className="border rounded px-3 py-2 w-36"
          placeholder="District"
          value={filters.district}
          onChange={(e) => setFilters({ ...filters, district: e.target.value })}
        />
        <input
          className="border rounded px-3 py-2 w-32"
          placeholder="Max ₹/unit"
          value={filters.price_max}
          onChange={(e) => setFilters({ ...filters, price_max: e.target.value })}
        />
        <button onClick={load} className="bg-leaf-600 text-white rounded px-4 py-2">
          Search
        </button>
      </div>

      {listings.length === 0 && <p className="text-gray-500">No produce found.</p>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {listings.map((l) => (
          <Link
            key={l.id}
            to={`/listings/${l.id}`}
            className="bg-white border rounded-xl p-4 hover:shadow"
          >
            <div className="flex justify-between items-start">
              <h3 className="font-semibold text-lg">
                {l.category}
                {l.variety ? ` · ${l.variety}` : ""}
              </h3>
              {l.grade && <span className="text-xs bg-gray-100 rounded px-2 py-0.5">Grade {l.grade}</span>}
            </div>
            <p className="text-leaf-700 font-bold mt-1">
              ₹{l.price_per_unit}/{l.unit.toLowerCase()}
            </p>
            <p className="text-sm text-gray-500 mt-1">
              {l.qty_available} {l.unit.toLowerCase()} available · min {l.min_order_qty}
            </p>
            <p className="text-sm text-gray-500">
              {l.district ?? "—"}
              {l.harvest_date ? ` · harvested ${l.harvest_date}` : ""}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
