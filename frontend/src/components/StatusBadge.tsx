const COLORS: Record<string, string> = {
  PLACED: "bg-gray-100 text-gray-700",
  PAID: "bg-blue-100 text-blue-700",
  ACCEPTED: "bg-indigo-100 text-indigo-700",
  PACKED: "bg-purple-100 text-purple-700",
  DISPATCHED: "bg-amber-100 text-amber-700",
  DELIVERED: "bg-green-100 text-green-700",
  SETTLED: "bg-green-200 text-green-800",
  DISPUTED: "bg-orange-100 text-orange-700",
  CANCELLED: "bg-red-100 text-red-700",
  REJECTED: "bg-red-100 text-red-700",
  REFUNDED: "bg-red-100 text-red-700",
};

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`text-xs font-medium rounded px-2 py-0.5 ${COLORS[status] ?? "bg-gray-100"}`}>
      {status}
    </span>
  );
}
