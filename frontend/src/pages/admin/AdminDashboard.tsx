import { Link } from "react-router-dom";
import { useAsync } from "../../hooks/useAsync";
import { apiGet } from "../../api/client";
import { fetchCompanies, fetchNews } from "../../api/mappers";
import StatCard from "../../components/StatCard";
import { LoadingState, ErrorState } from "../../components/States";

interface BackendCrawlRun {
  id: number;
  status: string;
  started_at: string;
  finished_at: string | null;
  articles_found: number;
  articles_new: number;
}

interface BackendUser {
  id: number;
  username: string;
  email: string;
  role: "admin" | "analyst" | "viewer";
  is_active: boolean;
}

const statusClass: Record<string, string> = {
  completed: "bg-positive/15 text-positive",
  failed: "bg-negative/15 text-negative",
  running: "bg-accent/15 text-accent",
  pending: "bg-[#1e2430] text-muted",
};

async function loadOverview() {
  const [companies, crawlRuns] = await Promise.all([
    fetchCompanies(),
    apiGet<BackendCrawlRun[]>("/api/admin/crawl-runs?limit=5"),
  ]);
  const [users, newsSample] = await Promise.all([
    apiGet<BackendUser[]>("/api/admin/users").catch(() => [] as BackendUser[]),
    fetchNews({ limit: 1000 }),
  ]);
  return { companies, crawlRuns, users, articleCount: newsSample.length };
}

export default function AdminDashboard() {
  const { data, loading, error, reload } = useAsync(loadOverview);

  if (loading) return <LoadingState label="Loading admin overview…" />;
  if (error) return <ErrorState title="Could not load overview" message={error} onRetry={reload} />;
  if (!data) return null;

  const activeUsers = data.users.filter((u) => u.is_active).length;

  return (
    <div>
      <header className="mb-5.5">
        <h1 className="text-[22px] font-semibold">Admin dashboard</h1>
        <p className="mt-1 text-sm text-muted">
          Platform health at a glance — crawlers, data collection and user accounts.
        </p>
      </header>

      <section className="mb-5 grid grid-cols-2 gap-3.5 lg:grid-cols-4">
        <StatCard
          label="Tracked companies"
          value={data.companies.length}
          sublabel="watchlist across all sectors"
        />
        <StatCard
          label="Categorized articles"
          value={data.articleCount}
          sublabel="latest 1000 fetched"
        />
        <StatCard
          label="Active users"
          value={data.users.length ? activeUsers : "—"}
          sublabel={data.users.length ? `${data.users.length} registered` : "users API unreachable"}
        />
        <StatCard
          label="Crawl runs shown"
          value={data.crawlRuns.length}
          sublabel={
            data.crawlRuns[0]
              ? `latest ${new Date(data.crawlRuns[0].started_at).toLocaleString()}`
              : "no runs yet"
          }
        />
      </section>

      <div className="mb-5 grid gap-5 lg:grid-cols-2">
        <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
          <h2 className="mb-3.5 text-[15px] font-semibold">Quick actions</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            <ActionCard
              to="/admin/crawl-runs"
              title="Trigger a crawl"
              desc="Run the portal crawlers and monitor run status."
            />
            <ActionCard
              to="/admin/news-review"
              title="Review news tags"
              desc="Fix mis-categorized articles; corrections persist."
            />
            <ActionCard
              to="/admin/users"
              title="Manage users"
              desc="Create accounts or deactivate existing ones."
            />
            <ActionCard
              to="/analysis"
              title="Open public analysis"
              desc="See what visitors see on the comparison page."
            />
          </div>
        </section>

        <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
          <div className="mb-3.5 flex items-center justify-between">
            <h2 className="text-[15px] font-semibold">Latest crawl runs</h2>
            <Link to="/admin/crawl-runs" className="text-xs text-accent hover:underline">
              Manage →
            </Link>
          </div>
          {data.crawlRuns.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted">
              No crawl runs recorded yet.
            </p>
          ) : (
            <ul className="flex flex-col">
              {data.crawlRuns.map((run) => (
                <li
                  key={run.id}
                  className="flex items-center justify-between border-b border-[#1e222c] py-2.5 last:border-b-0 last:pb-0"
                >
                  <div className="text-sm">
                    Run #{run.id}
                    <span className="ml-2 text-xs text-muted">
                      {new Date(run.started_at).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex items-center gap-2.5 text-xs">
                    <span className="tabular-nums text-muted">
                      {run.articles_new}/{run.articles_found} new
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] capitalize ${
                        statusClass[run.status] ?? statusClass.pending
                      }`}
                    >
                      {run.status}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}

function ActionCard({ to, title, desc }: { to: string; title: string; desc: string }) {
  return (
    <Link
      to={to}
      className="group rounded-lg border border-panel-border bg-[#171b24] px-3.5 py-3 transition hover:border-accent/40"
    >
      <div className="text-sm font-semibold group-hover:text-accent">{title}</div>
      <div className="mt-0.5 text-xs leading-relaxed text-muted">{desc}</div>
    </Link>
  );
}
