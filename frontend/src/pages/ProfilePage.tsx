import { useState } from "react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

export default function ProfilePage() {
  const { user, refreshMe } = useAuth();
  const [form, setForm] = useState({
    name: user?.name ?? "",
    district: user?.district ?? "",
    state: user?.state ?? "",
    pincode: user?.pincode ?? "",
  });
  const [payout, setPayout] = useState({ type: "UPI", vpa: "", account_number: "", ifsc: "" });
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  if (!user) return null;

  const saveProfile = async () => {
    setError("");
    setMsg("");
    try {
      await api.put("/me", form);
      await refreshMe();
      setMsg("Profile saved");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed");
    }
  };

  const savePayout = async () => {
    setError("");
    setMsg("");
    try {
      await api.put("/me/payout-account", {
        type: payout.type,
        vpa: payout.type === "UPI" ? payout.vpa : null,
        account_number: payout.type === "BANK" ? payout.account_number : null,
        ifsc: payout.type === "BANK" ? payout.ifsc : null,
      });
      setMsg("Payout account saved (penny-drop verified)");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed");
    }
  };

  const field = (key: keyof typeof form, label: string) => (
    <div>
      <label className="block text-sm font-medium mb-1">{label}</label>
      <input
        className="w-full border rounded px-3 py-2"
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
      />
    </div>
  );

  return (
    <div className="max-w-md mx-auto space-y-4">
      <div className="bg-white rounded-xl shadow p-6">
        <h2 className="text-xl font-bold mb-1">Profile</h2>
        <p className="text-sm text-gray-500 mb-4">
          {user.phone} · {user.role ?? "no role"} · {user.status}
        </p>
        <div className="space-y-3">
          {field("name", "Name")}
          {field("district", "District")}
          {field("state", "State")}
          {field("pincode", "PIN code")}
          <button onClick={saveProfile} className="btn-primary w-full">Save</button>
        </div>
      </div>

      {user.role === "FARMER" && (
        <div className="bg-white rounded-xl shadow p-6">
          <h3 className="font-semibold mb-3">Payout account</h3>
          <div className="space-y-3">
            <select
              className="w-full border rounded px-3 py-2"
              value={payout.type}
              onChange={(e) => setPayout({ ...payout, type: e.target.value })}
            >
              <option value="UPI">UPI</option>
              <option value="BANK">Bank account</option>
            </select>
            {payout.type === "UPI" ? (
              <input
                className="w-full border rounded px-3 py-2"
                placeholder="UPI ID (e.g. name@bank)"
                value={payout.vpa}
                onChange={(e) => setPayout({ ...payout, vpa: e.target.value })}
              />
            ) : (
              <>
                <input
                  className="w-full border rounded px-3 py-2"
                  placeholder="Account number"
                  value={payout.account_number}
                  onChange={(e) => setPayout({ ...payout, account_number: e.target.value })}
                />
                <input
                  className="w-full border rounded px-3 py-2"
                  placeholder="IFSC"
                  value={payout.ifsc}
                  onChange={(e) => setPayout({ ...payout, ifsc: e.target.value })}
                />
              </>
            )}
            <button onClick={savePayout} className="btn-primary w-full">Save payout account</button>
          </div>
        </div>
      )}

      {msg && <p className="text-green-700 text-sm">{msg}</p>}
      {error && <p className="text-red-600 text-sm">{error}</p>}
    </div>
  );
}
