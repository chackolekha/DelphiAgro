import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { OrderDetail } from "../types";
import StatusBadge from "../components/StatusBadge";

export default function OrderDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [detail, setDetail] = useState<OrderDetail | null>(null);
  const [error, setError] = useState("");
  const [otpInput, setOtpInput] = useState("");
  const [vehicle, setVehicle] = useState("");
  const [driver, setDriver] = useState("");
  const [disputeReason, setDisputeReason] = useState("");

  const load = useCallback(
    () => api.get<OrderDetail>(`/orders/${id}`).then(setDetail).catch((e) => setError(e.message)),
    [id],
  );
  useEffect(() => {
    load();
  }, [load]);

  if (!detail) return <p className="p-4">{error || "Loading…"}</p>;
  const { order, items, events, payments } = detail;
  const isFarmer = user?.id === order.farmer_id;
  const isRetailer = user?.id === order.retailer_id;

  const act = async (path: string, body?: unknown) => {
    setError("");
    try {
      setDetail(await api.post<OrderDetail>(`/orders/${id}/${path}`, body));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Action failed");
    }
  };

  const pay = async () => {
    setError("");
    try {
      await api.post(`/orders/${id}/payment`);
      // dev/stub provider: simulate the gateway capture
      await api.post("/payments/dev/capture", { order_id: id });
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Payment failed");
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      <Link to="/orders" className="text-sm text-leaf-700">← Back to orders</Link>

      <div className="bg-white border rounded-xl p-5">
        <div className="flex justify-between items-start">
          <h2 className="text-xl font-bold">Order #{order.id.slice(0, 8)}</h2>
          <StatusBadge status={order.status} />
        </div>
        <p className="text-sm text-gray-500">{new Date(order.created_at).toLocaleString()}</p>

        <table className="w-full text-sm mt-4">
          <thead>
            <tr className="text-left text-gray-500 border-b">
              <th className="py-1">Item</th><th>Qty</th><th>Rate</th><th className="text-right">Total</th>
            </tr>
          </thead>
          <tbody>
            {items.map((i) => (
              <tr key={i.id} className="border-b">
                <td className="py-1">{i.category ?? i.listing_id.slice(0, 8)}</td>
                <td>{i.quantity} {i.unit?.toLowerCase()}</td>
                <td>₹{i.price_per_unit}</td>
                <td className="text-right">₹{i.line_total}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="text-right mt-2 space-y-1">
          <p className="font-bold">Total ₹{order.total_amount}</p>
          {isFarmer && <p className="text-sm text-gray-500">Platform fee ₹{order.platform_fee}</p>}
        </div>

        {order.vehicle_no && (
          <p className="text-sm mt-2">Vehicle {order.vehicle_no} · Driver {order.driver_phone}</p>
        )}
        {detail.delivery_otp && ["DISPATCHED"].includes(order.status) && (
          <p className="mt-3 bg-amber-50 border border-amber-200 rounded p-3 text-sm">
            Share this delivery OTP on hand-over:{" "}
            <span className="font-mono font-bold text-lg">{detail.delivery_otp}</span>
          </p>
        )}
      </div>

      {/* Actions */}
      <div className="bg-white border rounded-xl p-5 space-y-3">
        <h3 className="font-semibold">Actions</h3>

        {isRetailer && order.status === "PLACED" && (
          <button onClick={pay} className="btn-primary">Pay ₹{order.total_amount} (dev)</button>
        )}
        {isFarmer && order.status === "PAID" && (
          <div className="flex gap-2">
            <button onClick={() => act("accept")} className="btn-primary">Accept</button>
            <button onClick={() => act("reject", { reason: "unavailable" })} className="btn-danger">
              Reject
            </button>
          </div>
        )}
        {isFarmer && order.status === "ACCEPTED" && (
          <button onClick={() => act("pack")} className="btn-primary">Mark packed</button>
        )}
        {isFarmer && order.status === "PACKED" && (
          <div className="space-y-2">
            <div className="flex gap-2">
              <input className="border rounded px-3 py-2 flex-1" placeholder="Vehicle no. (optional)"
                value={vehicle} onChange={(e) => setVehicle(e.target.value)} />
              <input className="border rounded px-3 py-2 flex-1" placeholder="Driver phone (optional)"
                value={driver} onChange={(e) => setDriver(e.target.value)} />
            </div>
            <button onClick={() => act("dispatch", { vehicle_no: vehicle || null, driver_phone: driver || null })}
              className="btn-primary">Dispatch</button>
          </div>
        )}
        {isFarmer && order.status === "DISPATCHED" && (
          <div className="flex gap-2">
            <input className="border rounded px-3 py-2 w-32" placeholder="Delivery OTP"
              maxLength={4} value={otpInput} onChange={(e) => setOtpInput(e.target.value)} />
            <button onClick={() => act("deliver", { otp: otpInput })} className="btn-primary">
              Confirm delivery
            </button>
          </div>
        )}
        {isRetailer && order.status === "DISPATCHED" && (
          <button onClick={() => act("deliver", {})} className="btn-primary">
            I received the produce
          </button>
        )}
        {isRetailer && ["DISPATCHED", "DELIVERED"].includes(order.status) && (
          <div className="flex gap-2">
            <input className="border rounded px-3 py-2 flex-1" placeholder="Dispute reason"
              value={disputeReason} onChange={(e) => setDisputeReason(e.target.value)} />
            <button
              onClick={() => act("dispute", { reason: disputeReason })}
              disabled={disputeReason.length < 5}
              className="btn-danger"
            >
              Raise dispute
            </button>
          </div>
        )}
        {["PLACED", "PAID", "ACCEPTED"].includes(order.status) && (isFarmer || isRetailer) && (
          <button onClick={() => act("cancel", { reason: "cancelled by user" })} className="btn-danger">
            Cancel order
          </button>
        )}
        {error && <p className="text-red-600 text-sm">{error}</p>}
      </div>

      {/* Payments */}
      {payments.length > 0 && (
        <div className="bg-white border rounded-xl p-5">
          <h3 className="font-semibold mb-2">Payments</h3>
          {payments.map((p) => (
            <div key={p.id} className="flex justify-between text-sm py-1 border-b last:border-0">
              <span>{p.type}</span>
              <span>{p.status}</span>
              <span>₹{p.amount}</span>
            </div>
          ))}
        </div>
      )}

      {/* Timeline */}
      <div className="bg-white border rounded-xl p-5">
        <h3 className="font-semibold mb-3">Timeline</h3>
        <ol className="relative border-l border-gray-200 ml-2 space-y-4">
          {events.map((e) => (
            <li key={e.id} className="ml-4">
              <div className="absolute w-3 h-3 bg-leaf-600 rounded-full -left-1.5 mt-1" />
              <p className="font-medium text-sm">{e.to_status}</p>
              <p className="text-xs text-gray-500">
                {new Date(e.created_at).toLocaleString()}
                {e.actor_role ? ` · ${e.actor_role}` : ""}
                {e.note ? ` — ${e.note}` : ""}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}
