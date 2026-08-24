import { NavLink, Navigate, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";
import Header, { Logo } from "./Header";
import { LoadingState } from "./States";

const adminNav = [
  { to: "/admin", label: "Admin Dashboard", end: true },
  { to: "/admin/crawl-runs", label: "Crawl Runs" },
  { to: "/admin/news-review", label: "News Review" },
  { to: "/admin/users", label: "Users" },
];

/**
 * Shell for /admin/* routes. Renders only for authenticated admins —
 * everyone else is redirected (to /admin/login when signed out, home
 * otherwise). Backend endpoints enforce the same rule server-side.
 */
export default function AdminLayout() {
  const { user, loading, logout } = useAuth();
  const navigate = useNavigate();

  if (loading) {
    return (
      <div className="flex min-h-screen flex-col">
        <Header />
        <LoadingState label="Checking session…" className="flex-1" />
      </div>
    );
  }

  if (!user) return <Navigate to="/admin/login" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;

  function handleLogout() {
    logout();
    navigate("/");
  }

  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <div className="border-b border-panel-border bg-[#0c0e13]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-2.5 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="rounded-md border border-accent/30 bg-accent/10 px-2 py-0.5 text-[11px] font-bold uppercase tracking-widest text-accent">
              Admin
            </span>
            <nav className="flex flex-wrap items-center gap-1" aria-label="Admin">
              {adminNav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `rounded-lg px-3 py-1.5 text-[13px] font-medium transition ${
                      isActive
                        ? "bg-[#1e2430] text-white"
                        : "text-muted hover:bg-[#1a1e28] hover:text-white"
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden text-xs text-muted sm:inline">
              {user.name}
            </span>
            <button
              onClick={handleLogout}
              className="rounded-lg border border-panel-border px-3 py-1.5 text-[13px] font-medium text-muted transition hover:border-negative/40 hover:bg-negative/10 hover:text-negative"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
      <main className="mx-auto w-full max-w-7xl flex-1 px-4 pb-16 pt-7 sm:px-6">
        <Outlet />
      </main>
      <footer className="border-t border-panel-border py-4">
        <div className="mx-auto max-w-7xl px-4 text-xs text-muted sm:px-6">
          <Logo />
        </div>
      </footer>
    </div>
  );
}
