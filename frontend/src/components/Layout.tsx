import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";

const NAV: Record<string, { to: string; label: string }[]> = {
  FARMER: [
    { to: "/farmer/listings", label: "My Listings" },
    { to: "/orders", label: "Orders" },
    { to: "/notifications", label: "Notifications" },
    { to: "/profile", label: "Profile" },
  ],
  RETAILER: [
    { to: "/browse", label: "Browse Produce" },
    { to: "/orders", label: "My Orders" },
    { to: "/notifications", label: "Notifications" },
    { to: "/profile", label: "Profile" },
  ],
  ADMIN: [
    { to: "/admin", label: "Admin Console" },
    { to: "/notifications", label: "Notifications" },
  ],
};

export default function Layout() {
  const { user, loading, logout } = useAuth();
  const loc = useLocation();

  if (loading) return <div className="p-8">Loading…</div>;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname }} />;
  if (!user.role && loc.pathname !== "/onboarding") return <Navigate to="/onboarding" />;

  const links = user.role ? NAV[user.role] : [];

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-leaf-700 text-white">
        <div className="max-w-5xl mx-auto flex items-center justify-between px-4 py-3">
          <Link to="/" className="font-bold text-lg">Delphi Agro</Link>
          <nav className="flex gap-4 text-sm items-center">
            {links.map((l) => (
              <Link key={l.to} to={l.to} className="hover:underline">{l.label}</Link>
            ))}
            {user.status !== "VERIFIED" && user.role && user.role !== "ADMIN" && (
              <Link to="/kyc" className="bg-yellow-400 text-yellow-900 px-2 py-0.5 rounded">
                {user.status === "KYC_SUBMITTED" ? "KYC pending" : "Verify account"}
              </Link>
            )}
            <button onClick={logout} className="underline">Logout</button>
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-5xl w-full mx-auto p-4">
        <Outlet />
      </main>
    </div>
  );
}
