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
import { fetchMarketOverview, latestQuote } from "../api/market";
import type { CompanyMarketRow } from "../api/market";
import { fetchNews, mapArticle } from "../api/mappers";
import type { NewsArticle } from "../types";
import type { MarketOverview } from "../api/market";

async function loadHome(): Promise<{ market: MarketOverview; news: NewsArticle[] }> {
  const market = await fetchMarketOverview();
  const raw = await fetchNews({ limit: 100 });
  return { market, news: raw.map((a) => mapArticle(a, market.companies)) };
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

  const { market, news } = data;
  const quotes = market.rows
    .map((row) => ({ row, quote: latestQuote(row) }))
    .filter((q) => q.quote !== null);

  const gainers = [...quotes]
    .filter((q) => q.quote!.changePct !== null)
    .sort((a, b) => b.quote!.changePct! - a.quote!.changePct!)
    .slice(0, 3);
  const losers = [...quotes]
    .filter((q) => q.quote!.changePct !== null)
    .sort((a, b) => a.quote!.changePct! - b.quote!.changePct!)
    .slice(0, 3);
  const mostActive = [...quotes]
    .sort((a, b) => b.quote!.volume - a.quote!.volume)
    .slice(0, 3);

  const totalVolume = quotes.reduce((sum, q) => sum + q.quote!.volume, 0);
  const advancers = quotes.filter((q) => (q.quote!.changePct ?? 0) > 0).length;
  const decliners = quotes.filter((q) => (q.quote!.changePct ?? 0) < 0).length;
  const anomalyCompanies = market.rows.filter(
    (r) => (r.summary?.anomalies?.count ?? 0) > 0,
  ).length;

  return (
    <div>
      {/* Ticker strip */}
      <div className="mb-6 overflow-hidden rounded-xl border border-panel-border bg-panel">
        <div className="flex items-center gap-5 overflow-x-auto px-4 py-2.5">
          <span className="shrink-0 text-[10px] font-bold uppercase tracking-widest text-accent">
            Watchlist
          </span>
          {quotes.length === 0 && !loading && (
            <span className="text-xs text-muted">No trading data yet</span>
          )}
          {quotes.map(({ row, quote }) => (
            <Link
              key={row.company.id}
              to={`/companies/${row.company.id}`}
              className="flex shrink-0 items-center gap-2 text-xs"
            >
              <span className="font-semibold">{row.company.symbol}</span>
              <span className="tabular-nums text-muted">
                Rs {quote!.price.toFixed(2)}
              </span>
              <ChangeBadge pct={quote!.changePct} arrow={false} className="text-[11px]" />
            </Link>
          ))}
        </div>
      </div>

      {/* Hero */}
      <section className="mb-6 rounded-2xl border border-panel-border bg-gradient-to-br from-panel via-panel to-[#131722] px-6 py-7 sm:px-8">
        <h1 className="max-w-xl text-2xl font-semibold leading-snug sm:text-[28px]">
          Track the Nepal Stock Exchange —{" "}
          <span className="text-accent">prices, volume and news</span> in one
          dashboard.
        </h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted">
          Live view of your tracked companies across banking, insurance,
          hydropower, manufacturing and hotels — powered by crawled news and
          daily OHLCV data.
        </p>
      </section>

      {/* Market stats */}
      <section className="mb-6 grid grid-cols-2 gap-3.5 lg:grid-cols-4">
        <StatCard label="Advancers" value={advancers} sublabel={`${decliners} decliners`} tone="positive" />
        <StatCard label="Decliners" value={decliners} sublabel={`${advancers} advancers`} tone={decliners > advancers ? "negative" : undefined} />
        <StatCard label="Total volume (last day)" value={totalVolume.toLocaleString()} />
        <StatCard
          label="Volume anomalies (30d)"
          value={`${anomalyCompanies} / ${market.rows.length} companies`}
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

      {/* Watchlist table */}
      <CompanyTableSection rows={market.rows} showAll />
    </div>
  );
}

function MoverList({
  rows,
  metric = "change",
}: {
  rows: { row: CompanyMarketRow; quote: ReturnType<typeof latestQuote> }[];
  metric?: "change" | "volume";
}) {
  if (rows.length === 0) return <p className="py-4 text-xs text-muted">No data</p>;
  return (
    <ul className="flex flex-col gap-2">
      {rows.map(({ row, quote }) => (
        <li key={row.company.id}>
          <Link
            to={`/companies/${row.company.id}`}
            className="flex items-center justify-between rounded-lg px-2 py-1.5 transition hover:bg-[#1e2430]"
          >
            <div>
              <div className="text-sm font-semibold">{row.company.symbol}</div>
              <div className="line-clamp-1 max-w-[160px] text-[11px] text-muted">
                {row.company.name}
              </div>
            </div>
            {metric === "volume" ? (
              <span className="text-xs tabular-nums text-muted">
                {quote!.volume.toLocaleString()}
              </span>
            ) : (
              <ChangeBadge pct={quote!.changePct} />
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
  rows: CompanyMarketRow[];
  showAll?: boolean;
}) {
  const sorted = [...rows].sort((a, b) =>
    a.company.symbol.localeCompare(b.company.symbol),
  );

  return (
    <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
      <div className="mb-3.5 flex items-center justify-between">
        <h2 className="text-[15px] font-semibold">Watchlist snapshot</h2>
        {!showAll && (
          <Link to="/companies" className="text-xs text-accent hover:underline">
            All companies →
          </Link>
        )}
      </div>
      {sorted.length === 0 ? (
        <EmptyState title="No companies found" hint="Seed companies via the backend scripts." />
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
                const quote = latestQuote(row);
                return (
                  <tr key={row.company.id} className="transition hover:bg-[#1a1f29]">
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5">
                      <div className="flex flex-col">
                        <span className="text-sm font-semibold">{row.company.symbol}</span>
                        <span className="text-xs text-muted">{row.company.name}</span>
                      </div>
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm text-muted">
                      {row.company.sector ?? "—"}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums">
                      {quote ? `Rs ${quote.price.toFixed(2)}` : "—"}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm">
                      <ChangeBadge pct={quote?.changePct ?? null} />
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums">
                      {quote ? quote.volume.toLocaleString() : "—"}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums text-muted">
                      {quote && quote.turnover > 0
                        ? `Rs ${quote.turnover.toLocaleString()}`
                        : "—"}
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-1.5">
                      <Sparkline values={row.prices.map((p) => p.close)} />
                    </td>
                    <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-right">
                      <Link
                        to={`/companies/${row.company.id}`}
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
      {sorted.some((r) => r.summary === null) && (
        <p className="mt-3 text-xs text-muted">
          Some companies lack enough price history for full behavior analysis —
          their trend metrics show limited values.
        </p>
      )}
    </section>
  );
}
