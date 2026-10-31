import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Listing } from "../types";

const EMPTY = {
  category: "",
  variety: "",
  grade: "",
  unit: "KG",
  price_per_unit: "",
  qty_available: "",
  min_order_qty: "1",
  district: "",
  pickup_location: "",
  harvest_date: "",
};

export default function FarmerListingsPage() {
  const { user } = useAuth();
  const [listings, setListings] = useState<Listing[]>([]);
  const [form, setForm] = useState(EMPTY);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    if (!user) return;
    setListings(
      await api.get<Listing[]>(`/listings?farmer_id=${user.id}&include_inactive=true`),
    );
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  const create = async () => {
    setError("");
    try {
      await api.post("/listings", {
        ...form,
        variety: form.variety || null,
        grade: form.grade || null,
        district: form.district || null,
        pickup_location: form.pickup_location || null,
        harvest_date: form.harvest_date || null,
      });
      setForm(EMPTY);
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to create listing");
    }
  };

  const deactivate = async (id: string) => {
    await api.del(`/listings/${id}`);
    await load();
  };

  const input = (key: keyof typeof EMPTY, label: string, type = "text") => (
    <div>
      <label className="block text-sm font-medium mb-1">{label}</label>
      <input
        type={type}
        className="w-full border rounded px-3 py-2"
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
      />
    </div>
  );

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">My listings</h2>
        <button onClick={() => setShowForm(!showForm)} className="btn-primary">
          {showForm ? "Close" : "+ New listing"}
        </button>
      </div>

      {showForm && (
        <div className="bg-white border rounded-xl p-5 mb-4 grid sm:grid-cols-2 gap-4">
          {input("category", "Category (e.g. Potato)")}
          {input("variety", "Variety")}
          {input("grade", "Grade")}
          <div>
            <label className="block text-sm font-medium mb-1">Unit</label>
            <select
              className="w-full border rounded px-3 py-2"
              value={form.unit}
              onChange={(e) => setForm({ ...form, unit: e.target.value })}
            >
              <option value="KG">KG</option>
              <option value="QUINTAL">QUINTAL</option>
              <option value="CRATE">CRATE</option>
            </select>
          </div>
          {input("price_per_unit", "Price per unit (₹)", "number")}
          {input("qty_available", "Quantity available", "number")}
          {input("min_order_qty", "Min order qty", "number")}
          {input("district", "District")}
          {input("pickup_location", "Pickup location")}
          {input("harvest_date", "Harvest date", "date")}
          <div className="sm:col-span-2">
            <button onClick={create} className="btn-primary">Create listing</button>
            {error && <p className="text-red-600 text-sm mt-2">{error}</p>}
          </div>
        </div>
      )}

      {listings.length === 0 && <p className="text-gray-500">No listings yet.</p>}
      <div className="space-y-2">
        {listings.map((l) => (
          <div key={l.id} className="flex items-center justify-between bg-white border rounded-lg px-4 py-3">
            <div>
              <p className="font-medium">
                {l.category} {l.variety && `· ${l.variety}`}{" "}
                {!l.active && <span className="text-xs text-red-500">(inactive)</span>}
              </p>
              <p className="text-sm text-gray-500">
                ₹{l.price_per_unit}/{l.unit.toLowerCase()} · {l.qty_available} available
              </p>
            </div>
            {l.active && (
              <button onClick={() => deactivate(l.id)} className="btn-danger text-sm">
                Deactivate
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
