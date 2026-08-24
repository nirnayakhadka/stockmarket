import { useState } from "react";
import { useAsync } from "../../hooks/useAsync";
import { apiGet, apiPost } from "../../api/client";
import { LoadingState, ErrorState, EmptyState } from "../../components/States";
import type { CrawlRun } from "../../types";

const statusClass: Record<CrawlRun["status"], string> = {
  completed: "bg-positive/15 text-positive",
  failed: "bg-negative/15 text-negative",
  running: "bg-accent/15 text-accent",
  pending: "bg-[#1e2430] text-muted",
};

interface BackendCrawlRun {
  id: number;
  status: string;
  portals: string;
  started_at: string;
  finished_at: string | null;
  articles_found: number;
  articles_new: number;
  articles_duplicate: number;
  errors: string | null;
}

const mapBackendCrawlRun = (backendRun: BackendCrawlRun): CrawlRun => {
  const started = new Date(backendRun.started_at);
  const finished = backendRun.finished_at ? new Date(backendRun.finished_at) : null;
  const durationSec = finished
    ? Math.round((finished.getTime() - started.getTime()) / 1000)
    : 0;

  let errorMsg: string | undefined;
  if (backendRun.errors) {
    try {
      const errList = JSON.parse(backendRun.errors);
      if (Array.isArray(errList) && errList.length > 0) {
        errorMsg = errList.map((e: any) => `${e.portal}: ${e.error}`).join("; ");
      } else {
        errorMsg = backendRun.errors;
      }
    } catch {
      errorMsg = backendRun.errors;
    }
  }

  return {
    id: `run-${backendRun.id}`,
    startedAt: backendRun.started_at,
    status: backendRun.status as CrawlRun["status"],
    articlesFound: backendRun.articles_found,
    durationSec,
    error: errorMsg,
  };
};

async function loadRuns(): Promise<BackendCrawlRun[]> {
  return apiGet<BackendCrawlRun[]>("/api/admin/crawl-runs?limit=50");
}

export default function CrawlRuns() {
  const { data, loading, error, reload } = useAsync(loadRuns);
  const [triggering, setTriggering] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [collecting, setCollecting] = useState(false);
  const [collectResult, setCollectResult] = useState<string | null>(null);

  async function triggerCrawl() {
    setTriggering(true);
    setActionError(null);
    try {
      await apiPost("/api/admin/crawl-runs", { portals: null });
      reload();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : "Failed to trigger crawl run");
    } finally {
      setTriggering(false);
    }
  }

  async function collectMarketData() {
    setCollecting(true);
    setCollectResult(null);
    try {
      const result = await apiPost<any>(
        "/api/admin/market-data/collect-sync?include_floorsheet=true",
        {},
      );
      const p = result.prices as any;
      const f = result.floorsheet as any;
      setCollectResult(
        `Prices: ${p?.inserted ?? 0} new / ${p?.updated ?? 0} updated (${p?.source ?? "?"}). ` +
          `Floorsheet: ${f?.inserted ?? 0} new (${f?.source ?? "n/a"}).`,
      );
      reload();
    } catch (err: unknown) {
      setCollectResult(
        `Error: ${err instanceof Error ? err.message : "Failed to collect market data"}`,
      );
    } finally {
      setCollecting(false);
    }
  }

  return (
    <div>
      <header className="mb-5.5">
        <h1 className="text-[22px] font-semibold">Crawl runs &amp; data collection</h1>
        <p className="mt-1 text-sm text-muted">
          Trigger news crawls across all four portals and refresh daily OHLCV +
          floorsheet data from NEPSE.
        </p>
      </header>

      <section className="mb-5 rounded-xl border border-panel-border bg-panel px-5 py-4.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-[15px] font-semibold">News crawling</h2>
            <p className="mt-0.5 text-xs text-muted">
              merolagani · sharesansar · nepsealpha · bizmandu — runs in the
              background; refresh to watch progress.
            </p>
          </div>
          <button
            onClick={triggerCrawl}
            disabled={triggering}
            className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-[#0c0e13] transition hover:bg-[#6fe0d5] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {triggering ? "Starting…" : "Trigger crawl"}
          </button>
        </div>
        {actionError && (
          <p className="mt-3 rounded-lg border border-negative/20 bg-negative/10 px-3 py-2 text-xs text-negative">
            {actionError}
          </p>
        )}
      </section>

      <section className="mb-5 rounded-xl border border-panel-border bg-panel px-5 py-4.5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-[15px] font-semibold">Trading data collection</h2>
            <p className="mt-0.5 text-xs text-muted">
              Pull today's OHLCV + floorsheet snapshot for the watchlist (falls back
              to synthetic data when the live NEPSE source is unavailable).
            </p>
          </div>
          <button
            onClick={collectMarketData}
            disabled={collecting}
            className="rounded-lg bg-accent px-3 py-1.5 text-xs font-semibold text-[#0c0e13] transition hover:bg-[#6fe0d5] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {collecting ? "Collecting…" : "Collect from NEPSE"}
          </button>
        </div>
        {collectResult && (
          <p className="mt-3 rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-xs text-muted">
            {collectResult}
          </p>
        )}
      </section>

      <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
        <div className="mb-3.5 flex items-center justify-between">
          <h2 className="text-[15px] font-semibold">Run history</h2>
          <button
            onClick={reload}
            className="rounded-lg border border-panel-border px-2.5 py-1 text-xs text-muted transition hover:bg-[#262d3b] hover:text-white"
          >
            Refresh
          </button>
        </div>

        {loading ? (
          <LoadingState label="Loading crawl runs…" className="min-h-0 py-6" />
        ) : error ? (
          <ErrorState title="Could not load crawl runs" message={error} onRetry={reload} />
        ) : (data ?? []).length === 0 ? (
          <EmptyState
            title="No crawl runs yet"
            hint="Trigger a crawl above — it will appear here immediately."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] border-collapse">
              <thead>
                <tr>
                  {["Run", "Portals", "Started", "Status", "Articles (new/found)", "Duration"].map(
                    (h) => (
                      <th
                        key={h}
                        className="border-b border-panel-border px-2.5 py-2 text-left text-[11px] uppercase tracking-wide text-muted"
                      >
                        {h}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {(data ?? []).map((r) => {
                  const mapped = mapBackendCrawlRun(r);
                  return (
                    <tr
                      key={r.id}
                      className="transition hover:bg-[#1a1f29]"
                      title={mapped.error || undefined}
                    >
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm font-medium">
                        #{r.id}
                      </td>
                      <td className="max-w-[220px] truncate border-b border-[#1e222c] px-2.5 py-2.5 text-xs text-muted">
                        {r.portals || "—"}
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm">
                        {new Date(r.started_at).toLocaleString()}
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[11px] capitalize ${statusClass[mapped.status]}`}
                        >
                          {mapped.status}
                        </span>
                        {mapped.error && (
                          <span className="ml-1.5 text-negative" title={mapped.error}>
                            ⚠
                          </span>
                        )}
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums">
                        {r.articles_new}/{r.articles_found}
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums text-muted">
                        {mapped.durationSec}s
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
