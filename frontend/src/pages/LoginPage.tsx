import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setTokens, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { User } from "../types";

export default function LoginPage() {
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [devOtp, setDevOtp] = useState<string | null>(null);
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [error, setError] = useState("");
  const { refreshMe } = useAuth();
  const nav = useNavigate();

  const requestOtp = async () => {
    setError("");
    try {
      const res = await api.post<{ dev_otp: string | null }>("/auth/otp/request", { phone });
      setDevOtp(res.dev_otp);
      setStep("otp");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to send OTP");
    }
  };

  const verify = async () => {
    setError("");
    try {
      const res = await api.post<{ access_token: string; refresh_token: string; user: User }>(
        "/auth/otp/verify",
        { phone, otp },
      );
      setTokens(res.access_token, res.refresh_token);
      await refreshMe();
      nav("/");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Verification failed");
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-leaf-50 p-4">
      <div className="bg-white rounded-xl shadow p-8 w-full max-w-sm">
        <h1 className="text-2xl font-bold text-leaf-700 mb-1">Delphi Agro</h1>
        <p className="text-sm text-gray-500 mb-6">Farm to retail, direct.</p>

        {step === "phone" ? (
          <>
            <label className="block text-sm font-medium mb-1">Mobile number</label>
            <input
              className="w-full border rounded px-3 py-2 mb-4"
              placeholder="+91XXXXXXXXXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <button
              onClick={requestOtp}
              className="w-full bg-leaf-600 text-white rounded py-2 font-medium"
            >
              Send OTP
            </button>
          </>
        ) : (
          <>
            <label className="block text-sm font-medium mb-1">Enter OTP</label>
            <input
              className="w-full border rounded px-3 py-2 mb-2 tracking-widest"
              placeholder="6-digit OTP"
              value={otp}
              onChange={(e) => setOtp(e.target.value)}
            />
            {devOtp && (
              <p className="text-xs text-gray-500 mb-3">
                Dev mode — OTP: <span className="font-mono font-bold">{devOtp}</span>
              </p>
            )}
            <button
              onClick={verify}
              className="w-full bg-leaf-600 text-white rounded py-2 font-medium"
            >
              Verify & Sign in
            </button>
          </>
        )}
        {error && <p className="text-red-600 text-sm mt-3">{error}</p>}
      </div>
    </div>
  );
}
