import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Role } from "../types";

export default function OnboardingPage() {
  const { user, refreshMe } = useAuth();
  const nav = useNavigate();
  const [form, setForm] = useState({
    name: user?.name ?? "",
    role: "" as Role | "",
    district: "",
    state: "",
    pincode: "",
    gstin: "",
  });
  const [error, setError] = useState("");

  const submit = async () => {
    if (!form.role || !form.name) {
      setError("Name and role are required");
      return;
    }
    try {
      await api.put("/me", { ...form, gstin: form.gstin || null });
      await refreshMe();
      nav("/kyc");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to save profile");
    }
  };

  const field = (key: keyof typeof form, label: string, required = false) => (
    <div>
      <label className="block text-sm font-medium mb-1">
        {label} {required && <span className="text-red-500">*</span>}
      </label>
      <input
        className="w-full border rounded px-3 py-2"
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
      />
    </div>
  );

  return (
    <div className="max-w-md mx-auto bg-white rounded-xl shadow p-6 mt-8">
      <h2 className="text-xl font-bold mb-4">Set up your account</h2>
      <div className="space-y-4">
        {field("name", "Full name", true)}
        <div>
          <label className="block text-sm font-medium mb-1">
            I am a <span className="text-red-500">*</span>
          </label>
          <div className="flex gap-3">
            {(["FARMER", "RETAILER"] as Role[]).map((r) => (
              <button
                key={r}
                onClick={() => setForm({ ...form, role: r })}
                className={`flex-1 border rounded py-3 font-medium ${
                  form.role === r ? "bg-leaf-600 text-white" : "bg-white"
                }`}
              >
                {r === "FARMER" ? "Farmer" : "Retailer"}
              </button>
            ))}
          </div>
        </div>
        {field("district", "District")}
        {field("state", "State")}
        {field("pincode", "PIN code")}
        {form.role === "RETAILER" && field("gstin", "GSTIN (optional)")}
        <button onClick={submit} className="w-full bg-leaf-600 text-white rounded py-2 font-medium">
          Continue to verification
        </button>
        {error && <p className="text-red-600 text-sm">{error}</p>}
      </div>
    </div>
  );
}
