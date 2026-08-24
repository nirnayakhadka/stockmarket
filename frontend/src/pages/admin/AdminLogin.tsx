import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../AuthContext";
import { Logo } from "../../components/Header";

export default function AdminLogin() {
  const { login, user, loading } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // Already authenticated as an admin? Straight to the dashboard.
  useEffect(() => {
    if (!loading && user?.role === "admin") navigate("/admin", { replace: true });
  }, [user, loading, navigate]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(username, password);
      navigate("/admin");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-[radial-gradient(circle_at_30%_20%,#1a2230,var(--color-bg))] px-4">
      <div className="mb-6">
        <Logo />
      </div>
      <form
        onSubmit={handleSubmit}
        className="w-[360px] rounded-2xl border border-panel-border bg-panel px-8 py-9"
      >
        <h1 className="text-xl font-semibold">Admin sign in</h1>
        <p className="mt-1 mb-5 text-sm text-muted">
          Restricted area — admin role required.
        </p>

        {error && (
          <div
            className="mb-3 rounded-lg border border-negative/20 bg-negative/10 px-3 py-2 text-xs text-negative"
            role="alert"
          >
            {error}
          </div>
        )}

        <div className="flex flex-col gap-3">
          <div>
            <label htmlFor="username" className="mb-1 block text-xs text-muted">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none focus:border-accent/50"
              autoComplete="username"
              required
            />
          </div>
          <div>
            <label htmlFor="password" className="mb-1 block text-xs text-muted">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none focus:border-accent/50"
              autoComplete="current-password"
              required
            />
          </div>
          <button
            type="submit"
            disabled={submitting}
            className="mt-2 rounded-lg bg-accent px-3.5 py-2 text-[13px] font-semibold text-[#0c0e13] transition hover:bg-[#6fe0d5] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </div>
      </form>
      <p className="mt-5 text-xs text-muted">
        Just browsing?{" "}
        <Link to="/" className="text-accent hover:underline">
          Return to the public dashboard
        </Link>
      </p>
    </div>
  );
}
