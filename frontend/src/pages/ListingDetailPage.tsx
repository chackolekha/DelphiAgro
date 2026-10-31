import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Listing, OrderDetail } from "../types";

export default function ListingDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const nav = useNavigate();
  const [listing, setListing] = useState<Listing | null>(null);
  const [qty, setQty] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get<Listing>(`/listings/${id}`).then(setListing).catch(() => setError("Listing not found"));
  }, [id]);

  if (!listing) return <p className="p-4">{error || "Loading…"}</p>;

  const canOrder = user?.role === "RETAILER" && user.status === "VERIFIED";

  const placeOrder = async () => {
    setBusy(true);
    setError("");
    try {
      const detail = await api.post<OrderDetail>(
        "/orders",
        { items: [{ listing_id: listing.id, quantity: qty }] },
        { "Idempotency-Key": crypto.randomUUID() },
      );
      nav(`/orders/${detail.order.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not place order");
      setBusy(false);
    }
  };

  return (
    <div className="max-w-xl mx-auto bg-white rounded-xl shadow p-6">
      <Link to="/browse" className="text-sm text-leaf-700">← Back to browse</Link>
      <h2 className="text-2xl font-bold mt-2">
        {listing.category} {listing.variety && `· ${listing.variety}`}
      </h2>
      <p className="text-leaf-700 font-bold text-xl mt-1">
        ₹{listing.price_per_unit}/{listing.unit.toLowerCase()}
      </p>
      <dl className="grid grid-cols-2 gap-2 text-sm mt-4">
        <dt className="text-gray-500">Available</dt>
        <dd>{listing.qty_available} {listing.unit.toLowerCase()}</dd>
        <dt className="text-gray-500">Min order</dt>
        <dd>{listing.min_order_qty} {listing.unit.toLowerCase()}</dd>
        <dt className="text-gray-500">District</dt>
        <dd>{listing.district ?? "—"}</dd>
        <dt className="text-gray-500">Pickup</dt>
        <dd>{listing.pickup_location ?? "—"}</dd>
        <dt className="text-gray-500">Harvest date</dt>
        <dd>{listing.harvest_date ?? "—"}</dd>
        {listing.grade && (
          <>
            <dt className="text-gray-500">Grade</dt>
            <dd>{listing.grade}</dd>
          </>
        )}
      </dl>

      {canOrder ? (
        <div className="mt-6 flex gap-2">
          <input
            className="border rounded px-3 py-2 w-32"
            placeholder={`Qty (${listing.unit.toLowerCase()})`}
            value={qty}
            onChange={(e) => setQty(e.target.value)}
          />
          <button
            onClick={placeOrder}
            disabled={busy || !qty}
            className="flex-1 bg-leaf-600 disabled:bg-gray-300 text-white rounded py-2 font-medium"
          >
            Place order
          </button>
        </div>
      ) : (
        <p className="mt-6 text-sm text-gray-500">
          {user?.role === "RETAILER"
            ? "Complete verification to place orders."
            : "Sign in as a retailer to order."}
        </p>
      )}
      {error && <p className="text-red-600 text-sm mt-3">{error}</p>}
    </div>
  );
}
