import { useState, type FormEvent } from "react";
import { useAsync } from "../../hooks/useAsync";
import { apiGet, apiPost, apiPatch } from "../../api/client";
import { LoadingState, ErrorState, EmptyState } from "../../components/States";

interface BackendUser {
  id: number;
  username: string;
  email: string;
  full_name: string | null;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
}

const roleClass: Record<string, string> = {
  admin: "bg-accent/15 text-accent",
  analyst: "bg-[#63b3ed]/15 text-[#63b3ed]",
  viewer: "bg-[#1e2430] text-muted",
};

async function loadUsers(): Promise<BackendUser[]> {
  return apiGet<BackendUser[]>("/api/admin/users");
}

export default function Users() {
  const { data, loading, error, reload } = useAsync(loadUsers);
  const [showForm, setShowForm] = useState(false);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<"admin" | "analyst" | "viewer">("viewer");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function createUser(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    setSubmitting(true);
    try {
      await apiPost("/api/admin/users", {
        username,
        email,
        password,
        full_name: fullName || null,
        role,
      });
      setShowForm(false);
      setUsername("");
      setEmail("");
      setFullName("");
      setPassword("");
      setRole("viewer");
      setNotice(`User "${username}" created.`);
      reload();
    } catch (err: unknown) {
      setFormError(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setSubmitting(false);
    }
  }

  async function deactivate(user: BackendUser) {
    if (!window.confirm(`Deactivate account "${user.username}"?`)) return;
    try {
      await apiPatch(`/api/admin/users/${user.id}/deactivate`);
      setNotice(`User "${user.username}" deactivated.`);
      reload();
    } catch (err: unknown) {
      setNotice(err instanceof Error ? err.message : "Failed to deactivate user");
    }
  }

  return (
    <div>
      <header className="mb-5.5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">Users &amp; roles</h1>
          <p className="mt-1 text-sm text-muted">
            Accounts managed here are enforced server-side via JWT + RBAC.
          </p>
        </div>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-[#0c0e13] transition hover:bg-[#6fe0d5]"
        >
          {showForm ? "Close form" : "+ Create user"}
        </button>
      </header>

      {notice && (
        <p className="mb-4 rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-xs text-muted">
          {notice}
        </p>
      )}

      {showForm && (
        <form
          onSubmit={createUser}
          className="mb-5 grid gap-3 rounded-xl border border-panel-border bg-panel px-5 py-4.5 sm:grid-cols-2 lg:grid-cols-3"
        >
          <label className="flex flex-col gap-1 text-xs text-muted">
            Username *
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none focus:border-accent/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted">
            Email *
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none focus:border-accent/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted">
            Password *
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none focus:border-accent/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted">
            Full name
            <input
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none focus:border-accent/50"
            />
          </label>
          <label className="flex flex-col gap-1 text-xs text-muted">
            Role
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as typeof role)}
              className="rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none focus:border-accent/50"
            >
              <option value="viewer">viewer</option>
              <option value="analyst">analyst</option>
              <option value="admin">admin</option>
            </select>
          </label>
          <div className="flex items-end gap-2">
            <button
              type="submit"
              disabled={submitting}
              className="rounded-lg bg-accent px-3.5 py-2 text-xs font-semibold text-[#0c0e13] transition hover:bg-[#6fe0d5] disabled:opacity-60"
            >
              {submitting ? "Creating…" : "Create user"}
            </button>
          </div>
          {formError && (
            <p className="text-xs text-negative sm:col-span-2 lg:col-span-3">{formError}</p>
          )}
        </form>
      )}

      {loading ? (
        <LoadingState label="Loading users…" />
      ) : error ? (
        <ErrorState title="Could not load users" message={error} onRetry={reload} />
      ) : (data ?? []).length === 0 ? (
        <EmptyState
          title="No users returned by the API"
          hint="Run seed_admin.py on the backend to create the first administrator."
        />
      ) : (
        <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] border-collapse">
              <thead>
                <tr>
                  {["ID", "Username", "Email", "Full name", "Role", "Status", ""].map((h) => (
                    <th
                      key={h}
                      className="border-b border-panel-border px-2.5 py-2 text-left text-[11px] uppercase tracking-wide text-muted"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(data ?? []).map((u) => (
                  <tr key={u.id} className="transition hover:bg-[#1a1f29]">
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums text-muted">
                      #{u.id}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm font-semibold">
                      {u.username}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm text-muted">
                      {u.email}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm">
                      {u.full_name || "—"}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5">
                      <span
                        className={`rounded-full px-2 py-0.5 text-[11px] capitalize ${roleClass[u.role]}`}
                      >
                        {u.role}
                      </span>
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm">
                      {u.is_active ? (
                        <span className="text-positive">Active</span>
                      ) : (
                        <span className="text-negative">Deactivated</span>
                      )}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-right">
                      {u.is_active && (
                        <button
                          onClick={() => deactivate(u)}
                          className="rounded-lg border border-panel-border px-2.5 py-1 text-xs text-muted transition hover:border-negative/40 hover:bg-negative/10 hover:text-negative"
                        >
                          Deactivate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
