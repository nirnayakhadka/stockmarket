import { Link } from "react-router-dom";
import StatCard from "../components/StatCard";
import ChangeBadge from "../components/ChangeBadge";
import Sparkline from "../components/Sparkline";
import {
  LoadingState,
  ErrorState,
  EmptyState,
} from "../components/States";
import { useAsync } from "../hooks/useAsync";
import {
  fetchMarketQuotes,
  fetchMarketSummary,
  quoteChangePct,
} from "../api/market";
import type {
  MarketQuoteRow,
  MarketSummaryResponse,
  ScripStat,
} from "../api/market";
import { fetchNews, mapArticle } from "../api/mappers";
import { fetchCompanies } from "../api/mappers";
import type { NewsArticle } from "../types";

async function loadHome(): Promise<{
  summary: MarketSummaryResponse;
  rows: MarketQuoteRow[];
  news: NewsArticle[];
}> {
  const [summary, quotesRes, raw, companies] = await Promise.all([
    fetchMarketSummary(),
    fetchMarketQuotes(),
    fetchNews({ limit: 100 }),
    fetchCompanies(),
  ]);
  const news = raw.map((a) => mapArticle(a, companies));
  return { summary, rows: quotesRes.quotes, news };
}

function nepseIndex(summary: MarketSummaryResponse) {
  return (
    summary.indices.find((i) => i.index_name === "NEPSE Index") ??
    summary.indices[0] ??
    null
  );
}

export default function Home() {
  const { data, loading, error, reload } = useAsync(loadHome);

  if (loading) return <LoadingState label="Loading market overview…" />;
  if (error)
    return (
      <ErrorState
        title="Could not load market data"
        message={error}
        onRetry={reload}
      />
    );
  if (!data) return null;

  const { summary, rows, news } = data;
  const idx = nepseIndex(summary);
  const quotes = rows.filter((r) => r.quote !== null);

  const gainers = summary.gainers.slice(0, 3);
  const losers = summary.losers.slice(0, 3);
  const mostActive = summary.volume_leaders.slice(0, 3);

  const { advancers, decliners, total_volume: totalVolume } = summary.breadth;

  return (
    <div>
      {/* Ticker strip */}
      <div className="mb-6 overflow-hidden rounded-xl border border-panel-border bg-panel">
        <div className="flex items-center gap-5 overflow-x-auto px-4 py-2.5">
          <span className="shrink-0 text-[10px] font-bold uppercase tracking-widest text-accent">
            NEPSE
          </span>
          {quotes.length === 0 && !loading && (
            <span className="text-xs text-muted">No trading data yet</span>
          )}
          {quotes.map((row) => (
            <Link
              key={row.company_id}
              to={`/companies/${row.company_id}`}
              className="flex shrink-0 items-center gap-2 text-xs"
            >
              <span className="font-semibold">{row.symbol}</span>
              <span className="tabular-nums text-muted">
                Rs {row.quote!.price.toFixed(2)}
              </span>
              <ChangeBadge pct={quoteChangePct(row)} arrow={false} className="text-[11px]" />
            </Link>
          ))}
        </div>
      </div>

      {/* Hero */}
      <section className="mb-6 rounded-2xl border border-panel-border bg-gradient-to-br from-panel via-panel to-[#131722] px-6 py-7 sm:px-8">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="max-w-xl text-2xl font-semibold leading-snug sm:text-[28px]">
              Track the Nepal Stock Exchange —{" "}
              <span className="text-accent">prices, volume and news</span> in
              one dashboard.
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
              Live view of every listed company across banking, insurance,
              hydropower, manufacturing and hotels — synced directly from the
              official NEPSE feed.
            </p>
          </div>
          {idx && (
            <div className="rounded-xl border border-panel-border bg-[#1a1f29] px-5 py-3 text-right">
              <div className="text-[10px] font-bold uppercase tracking-widest text-muted">
                {idx.index_name}
              </div>
              <div className="text-2xl font-semibold tabular-nums">
                {idx.value?.toLocaleString() ?? "—"}
              </div>
              <ChangeBadge pct={idx.pct_change} />
              {idx.business_date && (
                <div className="mt-0.5 text-[10px] text-muted">
                  as of {idx.business_date}
                  {summary.status.is_open ? " • market open" : ""}
                </div>
              )}
            </div>
          )}
        </div>
      </section>

      {/* Market stats */}
      <section className="mb-6 grid grid-cols-2 gap-3.5 lg:grid-cols-4">
        <StatCard label="Advancers" value={advancers} sublabel={`${decliners} decliners`} tone="positive" />
        <StatCard label="Decliners" value={decliners} sublabel={`${advancers} advancers`} tone={decliners > advancers ? "negative" : undefined} />
        <StatCard label="Total volume" value={totalVolume.toLocaleString()} sublabel={summary.trade_date ?? undefined} />
        <StatCard
          label="Total turnover"
          value={`Rs ${Math.round(summary.breadth.total_turnover).toLocaleString()}`}
          sublabel={`${rows.length} listed companies`}
        />
      </section>

      <div className="mb-6 grid gap-5 lg:grid-cols-2">
        {/* Top movers */}
        <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
          <div className="grid grid-cols-2 gap-5">
            <div>
              <h2 className="mb-3 flex items-center gap-1.5 text-[15px] font-semibold">
                <span className="inline-block h-2 w-2 rounded-full bg-positive" />
                Top gainers
              </h2>
              <MoverList rows={gainers} />
            </div>
            <div>
              <h2 className="mb-3 flex items-center gap-1.5 text-[15px] font-semibold">
                <span className="inline-block h-2 w-2 rounded-full bg-negative" />
                Top losers
              </h2>
              <MoverList rows={losers} />
            </div>
          </div>
          <div className="mt-4 border-t border-panel-border pt-3.5">
            <h3 className="mb-2.5 text-xs font-semibold uppercase tracking-wide text-muted">
              Most active by volume
            </h3>
            <MoverList rows={mostActive} metric="volume" />
          </div>
        </section>

        {/* Latest news */}
        <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
          <div className="mb-3.5 flex items-center justify-between">
            <h2 className="text-[15px] font-semibold">Latest categorized news</h2>
            <Link to="/news" className="text-xs text-accent hover:underline">
              View all →
            </Link>
          </div>
          {news.length === 0 ? (
            <EmptyState
              title="No articles yet"
              hint="Run a crawl from the admin panel to populate the news feed."
            />
          ) : (
            <ul className="flex flex-col">
              {news.slice(0, 5).map((item) => (
                <li
                  key={item.id}
                  className="border-b border-[#1e222c] py-2.5 last:border-b-0 last:pb-0"
                >
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="line-clamp-1 text-sm font-medium hover:text-accent hover:underline"
                  >
                    {item.headline}
                  </a>
                  <div className="mt-1 flex items-center gap-1.5 text-xs text-muted">
                    <span>{item.source}</span>
                    <span className="opacity-50">•</span>
                    <span>{new Date(item.publishedAt).toLocaleDateString()}</span>
                    {item.categorizations?.map((cat) => (
                      <span
                        key={cat.companyId}
                        className="rounded border border-accent/20 px-1.5 py-0.5 text-[10px] text-accent"
                      >
                        {cat.companySymbol}
                      </span>
                    ))}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* All companies table */}
      <CompanyTableSection rows={rows} showAll />
    </div>
  );
}

function MoverList({
  rows,
  metric = "change",
}: {
  rows: ScripStat[];
  metric?: "change" | "volume";
}) {
  if (rows.length === 0)
    return <p className="py-4 text-xs text-muted">No data</p>;
  return (
    <ul className="flex flex-col gap-2">
      {rows.map((s) => (
        <li key={s.symbol}>
          <Link
            to={`/companies/${s.company_id}`}
            className="flex items-center justify-between rounded-lg px-2 py-1.5 transition hover:bg-[#1e2430]"
          >
            <div>
              <div className="text-sm font-semibold">{s.symbol}</div>
              <div className="line-clamp-1 max-w-[160px] text-[11px] text-muted">
                {s.name}
              </div>
            </div>
            {metric === "volume" ? (
              <span className="text-xs tabular-nums text-muted">
                {s.volume.toLocaleString()}
              </span>
            ) : (
              <ChangeBadge pct={s.change_pct} />
            )}
          </Link>
        </li>
      ))}
    </ul>
  );
}

export function CompanyTableSection({
  rows,
  showAll = false,
}: {
  rows: MarketQuoteRow[];
  showAll?: boolean;
}) {
  const sorted = [...rows].sort((a, b) =>
    a.symbol.localeCompare(b.symbol),
  );

  return (
    <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
      <div className="mb-3.5 flex items-center justify-between">
        <h2 className="text-[15px] font-semibold">
          {showAll ? "All listed companies" : "Watchlist snapshot"}
        </h2>
        {!showAll && (
          <Link to="/companies" className="text-xs text-accent hover:underline">
            All companies →
          </Link>
        )}
      </div>
      {sorted.length === 0 ? (
        <EmptyState
          title="No companies found"
          hint="The backend syncs companies automatically at startup from the official NEPSE list."
        />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[720px] border-collapse">
            <thead>
              <tr>
                {["Company", "Sector", "Close", "Change", "Volume", "Turnover", "30d trend", ""].map(
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
              {sorted.map((row) => {
                const q = row.quote;
                return (
                  <tr key={row.company_id} className="transition hover:bg-[#1a1f29]">
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold">{row.symbol}</span>
                        <span className="text-xs text-muted">{row.name}</span>
                      </div>
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm text-muted">
                      {row.sector ?? "—"}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums">
                      {q ? `Rs ${q.price.toFixed(2)}` : "—"}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm">
                      <ChangeBadge pct={q?.change_pct ?? null} />
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums">
                      {q ? q.volume.toLocaleString() : "—"}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums text-muted">
                      {q && q.turnover
                        ? `Rs ${q.turnover.toLocaleString()}`
                        : "—"}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-1.5">
                      <Sparkline values={row.history.map((h) => h.close)} />
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-right">
                      <Link
                        to={`/companies/${row.company_id}`}
                        className="inline-block rounded-lg border border-panel-border bg-[#1e2430] px-2.5 py-1 text-xs font-medium transition hover:bg-[#262d3b]"
                      >
                        View
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
