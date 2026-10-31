import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Notification } from "../types";

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([]);

  useEffect(() => {
    api.get<Notification[]>("/notifications").then(setItems).catch(() => {});
  }, []);

  const markRead = async (id: string) => {
    await api.post(`/notifications/${id}/read`);
    setItems(items.map((n) => (n.id === id ? { ...n, read_at: new Date().toISOString() } : n)));
  };

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">Notifications</h2>
      {items.length === 0 && <p className="text-gray-500">Nothing yet.</p>}
      <div className="space-y-2">
        {items.map((n) => (
          <button
            key={n.id}
            onClick={() => markRead(n.id)}
            className={`w-full text-left border rounded-lg px-4 py-3 ${
              n.read_at ? "bg-white" : "bg-leaf-50 border-leaf-200"
            }`}
          >
            <p className="font-medium">{n.title}</p>
            <p className="text-sm text-gray-600">{n.body}</p>
            <p className="text-xs text-gray-400 mt-1">{new Date(n.created_at).toLocaleString()}</p>
          </button>
        ))}
      </div>
    </div>
  );
}
