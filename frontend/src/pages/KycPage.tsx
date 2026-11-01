import { useEffect, useState } from "react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";

interface KycStatus {
  user_status: string;
  review_status: string | null;
  reject_reason: string | null;
  submitted_at: string | null;
}

export default function KycPage() {
  const { refreshMe } = useAuth();
  const [status, setStatus] = useState<KycStatus | null>(null);
  const [form, setForm] = useState({ kyc_name: "", kyc_dob: "", aadhaar_last4: "" });
  const [consent, setConsent] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  const load = () => api.get<KycStatus>("/kyc/status").then(setStatus).catch(() => {});
  useEffect(() => {
    load();
  }, []);

  const submit = async () => {
    setError("");
    try {
      await api.post("/kyc/submit", {
        consent,
        method: "MANUAL_DOC",
        kyc_name: form.kyc_name,
        kyc_dob: form.kyc_dob,
        aadhaar_last4: form.aadhaar_last4 || null,
      });
      setDone(true);
      await refreshMe();
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Submission failed");
    }
  };

  if (status?.user_status === "VERIFIED")
    return <Banner kind="ok" text="Your account is verified. You can trade now." />;
  if (done || status?.review_status === "PENDING")
    return <Banner kind="info" text="KYC submitted. An admin will review your details shortly." />;

  return (
    <div className="max-w-md mx-auto bg-white rounded-xl shadow p-6 mt-8">
      <h2 className="text-xl font-bold mb-1">Identity verification</h2>
      <p className="text-sm text-gray-500 mb-4">
        MVP: submit your ID details for manual admin review (Aadhaar eKYC via DigiLocker coming).
      </p>
      {status?.reject_reason && (
        <Banner kind="err" text={`Previous submission rejected: ${status.reject_reason}`} />
      )}
      <div className="space-y-4 mt-4">
        <div>
          <label className="block text-sm font-medium mb-1">Name (as on ID)</label>
          <input
            className="w-full border rounded px-3 py-2"
            value={form.kyc_name}
            onChange={(e) => setForm({ ...form, kyc_name: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Date of birth</label>
          <input
            type="date"
            className="w-full border rounded px-3 py-2"
            value={form.kyc_dob}
            onChange={(e) => setForm({ ...form, kyc_dob: e.target.value })}
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Aadhaar last 4 digits (optional)</label>
          <input
            className="w-full border rounded px-3 py-2"
            maxLength={4}
            value={form.aadhaar_last4}
            onChange={(e) => setForm({ ...form, aadhaar_last4: e.target.value })}
          />
        </div>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            checked={consent}
            onChange={(e) => setConsent(e.target.checked)}
            className="mt-1"
          />
          I consent to Delphi Agro verifying my identity and storing the submitted details for
          review purposes.
        </label>
        <button
          onClick={submit}
          disabled={!consent}
          className="w-full bg-leaf-600 disabled:bg-gray-300 text-white rounded py-2 font-medium"
        >
          Submit for review
        </button>
        {error && <p className="text-red-600 text-sm">{error}</p>}
      </div>
    </div>
  );
}

function Banner({ kind, text }: { kind: "ok" | "info" | "err"; text: string }) {
  const cls = {
    ok: "bg-green-50 text-green-800 border-green-200",
    info: "bg-blue-50 text-blue-800 border-blue-200",
    err: "bg-red-50 text-red-800 border-red-200",
  }[kind];
  return <div className={`border rounded p-4 ${cls}`}>{text}</div>;
}
