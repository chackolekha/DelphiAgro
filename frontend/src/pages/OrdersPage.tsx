import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { Order } from "../types";
import StatusBadge from "../components/StatusBadge";

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([]);

  useEffect(() => {
    api.get<Order[]>("/orders").then(setOrders).catch(() => {});
  }, []);

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Orders</h2>
      {orders.length === 0 && <p className="text-gray-500">No orders yet.</p>}
      <div className="space-y-2">
        {orders.map((o) => (
          <Link
            key={o.id}
            to={`/orders/${o.id}`}
            className="flex items-center justify-between bg-white border rounded-lg px-4 py-3 hover:shadow"
          >
            <div>
              <p className="font-medium">#{o.id.slice(0, 8)}</p>
              <p className="text-sm text-gray-500">
                {new Date(o.created_at).toLocaleString()}
              </p>
            </div>
            <div className="text-right">
              <p className="font-bold">₹{o.total_amount}</p>
              <StatusBadge status={o.status} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
