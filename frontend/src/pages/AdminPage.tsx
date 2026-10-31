import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Dispute, KycQueueItem, Order, User } from "../types";
import StatusBadge from "../components/StatusBadge";
import { Navigate } from "react-router-dom";

type Tab = "kyc" | "disputes" | "orders" | "users";

export default function AdminPage() {
  const { user } = useAuth();
  const [tab, setTab] = useState<Tab>("kyc");
  if (user && user.role !== "ADMIN") return <Navigate to="/" />;

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Admin console</h2>
      <div className="flex gap-2 mb-4">
        {(["kyc", "disputes", "orders", "users"] as Tab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded font-medium ${
              tab === t ? "bg-leaf-600 text-white" : "bg-white border"
            }`}
          >
            {t === "kyc" ? "KYC queue" : t[0].toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      {tab === "kyc" && <KycTab />}
      {tab === "disputes" && <DisputesTab />}
      {tab === "orders" && <OrdersTab />}
      {tab === "users" && <UsersTab />}
    </div>
  );
}

function KycTab() {
  const [items, setItems] = useState<KycQueueItem[]>([]);
  const [error, setError] = useState("");

  const load = useCallback(
    () => api.get<KycQueueItem[]>("/admin/kyc?status=PENDING").then(setItems).catch(() => {}),
    [],
  );
  useEffect(() => {
    load();
  }, [load]);

  const act = async (id: string, action: "approve" | "reject") => {
    setError("");
    try {
      const reason =
        action === "reject" ? window.prompt("Rejection reason") ?? "rejected" : undefined;
      await api.post(`/admin/kyc/${id}/${action}`, action === "reject" ? { reason } : undefined);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed");
    }
  };

  return (
    <div className="space-y-2">
      {items.length === 0 && <p className="text-gray-500">Queue is empty.</p>}
      {items.map((k) => (
        <div key={k.id} className="bg-white border rounded-lg p-4 flex justify-between items-start">
          <div>
            <p className="font-medium">{k.kyc_name ?? "—"} <span className="text-gray-400">({k.user_role})</span></p>
            <p className="text-sm text-gray-500">
              Profile: {k.user_name ?? "—"} · {k.user_phone} · DOB {k.kyc_dob ?? "—"} ·
              Aadhaar ••••{k.aadhaar_last4 ?? "—"} · {k.method}
            </p>
          </div>
          <div className="flex gap-2">
            <button onClick={() => act(k.id, "approve")} className="btn-primary">Approve</button>
            <button onClick={() => act(k.id, "reject")} className="btn-danger">Reject</button>
          </div>
        </div>
      ))}
      {error && <p className="text-red-600 text-sm">{error}</p>}
    </div>
  );
}

function DisputesTab() {
  const [disputes, setDisputes] = useState<Dispute[]>([]);
  const load = useCallback(
    () => api.get<Dispute[]>("/admin/disputes?status=OPEN").then(setDisputes).catch(() => {}),
    [],
  );
  useEffect(() => {
    load();
  }, [load]);

  const resolve = async (id: string, resolution: "RELEASE" | "REFUND") => {
    await api.post(`/admin/disputes/${id}/resolve`, { resolution });
    await load();
  };

  return (
    <div className="space-y-2">
      {disputes.length === 0 && <p className="text-gray-500">No open disputes.</p>}
      {disputes.map((d) => (
        <div key={d.id} className="bg-white border rounded-lg p-4">
          <p className="font-medium">Order #{d.order_id.slice(0, 8)}</p>
          <p className="text-sm text-gray-600 mt-1">{d.reason}</p>
          <div className="flex gap-2 mt-3">
            <button onClick={() => resolve(d.id, "RELEASE")} className="btn-primary text-sm">
              Release payout to farmer
            </button>
            <button onClick={() => resolve(d.id, "REFUND")} className="btn-danger text-sm">
              Refund retailer
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function OrdersTab() {
  const [orders, setOrders] = useState<Order[]>([]);
  useEffect(() => {
    api.get<Order[]>("/admin/orders").then(setOrders).catch(() => {});
  }, []);
  return (
    <div className="space-y-2">
      {orders.map((o) => (
        <div key={o.id} className="flex justify-between bg-white border rounded-lg px-4 py-3">
          <div>
            <p className="font-medium">#{o.id.slice(0, 8)}</p>
            <p className="text-xs text-gray-500">
              farmer {o.farmer_id.slice(0, 8)} · retailer {o.retailer_id.slice(0, 8)}
            </p>
          </div>
          <div className="text-right">
            <p className="font-bold">₹{o.total_amount}</p>
            <StatusBadge status={o.status} />
          </div>
        </div>
      ))}
    </div>
  );
}

function UsersTab() {
  const [users, setUsers] = useState<User[]>([]);
  const load = useCallback(
    () => api.get<User[]>("/admin/users").then(setUsers).catch(() => {}),
    [],
  );
  useEffect(() => {
    load();
  }, [load]);

  const toggle = async (u: User) => {
    const action = u.status === "SUSPENDED" ? "reactivate" : "suspend";
    await api.post(`/admin/users/${u.id}/${action}`);
    await load();
  };

  return (
    <div className="space-y-2">
      {users.map((u) => (
        <div key={u.id} className="flex justify-between items-center bg-white border rounded-lg px-4 py-3">
          <div>
            <p className="font-medium">{u.name ?? u.phone} <span className="text-gray-400">({u.role ?? "no role"})</span></p>
            <p className="text-xs text-gray-500">{u.status} · {u.district ?? "—"}</p>
          </div>
          {u.role !== "ADMIN" && (
            <button onClick={() => toggle(u)} className="btn-danger text-sm">
              {u.status === "SUSPENDED" ? "Reactivate" : "Suspend"}
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
