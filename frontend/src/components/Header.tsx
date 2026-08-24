import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../AuthContext";

const publicNav = [
  { to: "/", label: "Home", end: true },
  { to: "/companies", label: "Markets" },
  { to: "/news", label: "News" },
  { to: "/analysis", label: "Analysis" },
];

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5">
      <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-2 font-extrabold text-[#0c0e13]">
        N
      </span>
      <span className="text-[15px] font-bold tracking-tight">
        NEPSE<span className="text-accent"> Pulse</span>
      </span>
    </Link>
  );
}

/** Top navigation bar used on every public and admin page. */
export default function Header() {
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);

  function handleLogout() {
    logout();
    navigate("/");
  }

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `rounded-lg px-3 py-1.5 text-[13px] font-medium transition ${
      isActive
        ? "bg-[#1e2430] text-white"
        : "text-muted hover:bg-[#1a1e28] hover:text-white"
    }`;

  return (
    <header className="sticky top-0 z-40 border-b border-panel-border bg-[#0c0e13]/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Logo />
          <nav
            className="hidden items-center gap-1 md:flex"
            aria-label="Primary"
          >
            {publicNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={linkClass}
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="hidden items-center gap-2.5 md:flex">
          {!loading && user?.role === "admin" ? (
            <>
              <NavLink to="/admin" end className={linkClass}>
                Admin Dashboard
              </NavLink>
              <button
                onClick={handleLogout}
                className="rounded-lg border border-panel-border px-3 py-1.5 text-[13px] font-medium text-muted transition hover:border-negative/40 hover:bg-negative/10 hover:text-negative"
              >
                Logout
              </button>
            </>
          ) : (
            <>
              {!loading && user && (
                <span className="text-xs text-muted">
                  Signed in as{" "}
                  <span className="font-semibold text-white">{user.name}</span>
                </span>
              )}
              <Link
                to="/admin/login"
                className="rounded-lg bg-accent px-3.5 py-1.5 text-[13px] font-semibold text-[#0c0e13] transition hover:bg-[#6fe0d5]"
              >
                Admin Sign In
              </Link>
            </>
          )}
        </div>

        <button
          className="rounded-lg border border-panel-border p-2 md:hidden"
          onClick={() => setMobileOpen((o) => !o)}
          aria-label="Toggle menu"
          aria-expanded={mobileOpen}
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="h-4 w-4"
            aria-hidden="true"
          >
            {mobileOpen ? (
              <path strokeLinecap="round" d="M6 6l12 12M18 6L6 18" />
            ) : (
              <path strokeLinecap="round" d="M4 7h16M4 12h16M4 17h16" />
            )}
          </svg>
        </button>
      </div>

      {mobileOpen && (
        <nav
          className="flex flex-col gap-1 border-t border-panel-border bg-[#0c0e13] px-4 py-3 md:hidden"
          aria-label="Mobile"
        >
          {publicNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive ? "bg-[#1e2430] text-white" : "text-muted hover:text-white"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
          <div className="mt-2 border-t border-panel-border pt-3">
            {user?.role === "admin" ? (
              <>
                <Link
                  to="/admin"
                  onClick={() => setMobileOpen(false)}
                  className="block rounded-lg px-3 py-2 text-sm font-medium text-muted hover:text-white"
                >
                  Admin Dashboard
                </Link>
                <button
                  onClick={() => {
                    setMobileOpen(false);
                    handleLogout();
                  }}
                  className="block w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-muted hover:text-negative"
                >
                  Logout
                </button>
              </>
            ) : (
              <Link
                to="/admin/login"
                onClick={() => setMobileOpen(false)}
                className="block rounded-lg bg-accent px-3 py-2 text-center text-sm font-semibold text-[#0c0e13]"
              >
                Admin Sign In
              </Link>
            )}
          </div>
        </nav>
      )}
    </header>
  );
}
