import { useMemo } from "react";
import { Link } from "react-router-dom";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import StatCard from "../components/StatCard";
import ChangeBadge from "../components/ChangeBadge";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { fetchMarketOverview } from "../api/market";
import type { CompanyMarketRow } from "../api/market";
import { fetchNews, mapArticle } from "../api/mappers";
import type { MarketOverview } from "../api/market";

const LINE_COLORS = [
  "#4fd1c5",
  "#f6ad55",
  "#63b3ed",
  "#f687b3",
  "#9ae6b4",
  "#faf089",
  "#b794f4",
  "#fc8181",
  "#76e4f7",
  "#f0fff4",
];

async function loadAnalysis(): Promise<{
  market: MarketOverview;
  newsCounts: Record<number, number>;
}> {
  const market = await fetchMarketOverview();
  const raw = await fetchNews({ limit: 500 });
  const articles = raw.map((a) => mapArticle(a, market.companies));
  const newsCounts: Record<number, number> = {};
  for (const article of articles) {
    for (const cid of article.companyIds) {
      const id = Number(cid);
      newsCounts[id] = (newsCounts[id] ?? 0) + 1;
    }
  }
  return { market, newsCounts };
}

/** Cumulative % change per company normalized to 0 at the first common date. */
function buildComparisonSeries(rows: CompanyMarketRow[]) {
  const seriesByCompany = rows
    .filter((r) => r.prices.length >= 2)
    .map((r) => {
      const base = r.prices[0].close || 1;
      return {
        company: r.company,
        points: r.prices.map((p) => ({
          date: p.date,
          pct: ((p.close - base) / base) * 100,
        })),
      };
    });

  // Align by index (all companies share the same trading calendar in the dataset).
  return seriesByCompany;
}

export default function Analysis() {
  const { data, loading, error, reload } = useAsync(loadAnalysis);

  const series = useMemo(
    () => buildComparisonSeries(data?.market.rows ?? []),
    [data],
  );

  const chartData = useMemo(() => {
    // Merge every company's cumulative % change into rows keyed by date.
    const byDate = new Map<string, Record<string, number>>();
    series.forEach(({ company, points }) => {
      points.forEach((p) => {
        const rowMap = byDate.get(p.date) ?? {};
        rowMap[company.symbol] = Number(p.pct.toFixed(2));
        byDate.set(p.date, rowMap);
      });
    });
    return Array.from(byDate.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, values]) => ({ date, ...values }));
  }, [series]);

  const ranked = useMemo(
    () =>
      [...(data?.market.rows ?? [])]
        .map((row) => ({
          row,
          quoteChange: row.summary?.price_trend?.total_change_pct ?? null,
          avgVolume: row.summary?.volume_trend?.avg_volume ?? 0,
          anomalies: row.summary?.anomalies?.count ?? 0,
          pressure: row.summary?.pressure_summary ?? {},
          inNews: data?.newsCounts[row.company.id] ?? 0,
        }))
        .sort((a, b) => b.avgVolume - a.avgVolume),
    [data],
  );

  if (loading) return <LoadingState label="Crunching cross-company analytics…" />;
  if (error)
    return (
      <ErrorState title="Could not load analysis" message={error} onRetry={reload} />
    );
  if (!data) return null;

  const bestPerformer = [...ranked]
    .filter((r) => r.quoteChange !== null)
    .sort((a, b) => (b.quoteChange ?? 0) - (a.quoteChange ?? 0))[0];
  const worstPerformer = [...ranked]
    .filter((r) => r.quoteChange !== null)
    .sort((a, b) => (a.quoteChange ?? 0) - (b.quoteChange ?? 0))[0];
  const mostInNews = [...ranked].sort((a, b) => b.inNews - a.inNews)[0];

  return (
    <div>
      <header className="mb-5.5">
        <h1 className="text-[22px] font-semibold">Analysis — cross-company comparison</h1>
        <p className="mt-1 text-sm text-muted">
          Side-by-side behavior of the tracked watchlist over the last 30 days.
        </p>
      </header>

      {ranked.length === 0 ? (
        <EmptyState
          title="No analysis data"
          hint="Seed companies and daily prices on the backend, then reload this page."
          action={
            <button onClick={reload} className="rounded-lg border border-panel-border bg-[#1e2430] px-3 py-1.5 text-xs font-medium hover:bg-[#262d3b]">
              Reload
            </button>
          }
        />
      ) : (
        <>
          <section className="mb-5 grid grid-cols-2 gap-3.5 lg:grid-cols-4">
            <StatCard
              label="Best performer (30d)"
              value={
                bestPerformer
                  ? `${bestPerformer.row.company.symbol} ${bestPerformer.quoteChange! >= 0 ? "+" : ""}${bestPerformer.quoteChange!.toFixed(2)}%`
                  : "—"
              }
              tone={bestPerformer && bestPerformer.quoteChange! >= 0 ? "positive" : "negative"}
            />
            <StatCard
              label="Worst performer (30d)"
              value={
                worstPerformer
                  ? `${worstPerformer.row.company.symbol} ${worstPerformer.quoteChange! >= 0 ? "+" : ""}${worstPerformer.quoteChange!.toFixed(2)}%`
                  : "—"
              }
              tone={worstPerformer && worstPerformer.quoteChange! >= 0 ? "positive" : "negative"}
            />
            <StatCard
              label="Most active (avg vol)"
              value={ranked[0]?.row.company.symbol ?? "—"}
              sublabel={ranked[0] ? ranked[0].avgVolume.toLocaleString() : undefined}
            />
            <StatCard
              label="Most in news (30d)"
              value={mostInNews && mostInNews.inNews > 0 ? `${mostInNews.row.company.symbol} (${mostInNews.inNews})` : "—"}
            />
          </section>

          {/* Normalized performance */}
          <section className="mb-5 rounded-xl border border-panel-border bg-panel px-5 py-4.5">
            <h2 className="mb-1 text-[15px] font-semibold">
              Cumulative % change — last 30 days
            </h2>
            <p className="mb-3.5 text-xs text-muted">
              All companies rebased to 0% at the start of the window for direct comparison.
            </p>
            {chartData.length > 1 ? (
              <ResponsiveContainer width="100%" height={360}>
                <LineChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={30} />
                  <YAxis tick={{ fontSize: 11 }} unit="%" width={52} />
                  <Tooltip
                    contentStyle={{
                      background: "#1b1f27",
                      border: "1px solid #333",
                      fontSize: 12,
                    }}
                    formatter={(v) => `${Number(v).toFixed(2)}%`}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                  {series.map(({ company }, i) => (
                    <Line
                      key={company.id}
                      type="monotone"
                      dataKey={company.symbol}
                      stroke={LINE_COLORS[i % LINE_COLORS.length]}
                      strokeWidth={2}
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <EmptyState
                title="Not enough price history"
                hint="At least two days of prices per company are required for the comparison chart."
              />
            )}
          </section>

          {/* Avg volume comparison */}
          <section className="mb-5 rounded-xl border border-panel-border bg-panel px-5 py-4.5">
            <h2 className="mb-3.5 text-[15px] font-semibold">Average daily volume</h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={ranked.map((r) => ({
                  symbol: r.row.company.symbol,
                  volume: r.avgVolume,
                }))} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
                <XAxis dataKey="symbol" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} width={70} tickFormatter={(v) => v.toLocaleString()} />
                <Tooltip
                  contentStyle={{ background: "#1b1f27", border: "1px solid #333", fontSize: 12 }}
                  formatter={(v) => Number(v).toLocaleString()}
                />
                <Bar dataKey="volume" fill="#4fd1c5" radius={[4, 4, 0, 0]} maxBarSize={46} />
              </BarChart>
            </ResponsiveContainer>
          </section>

          {/* Comparison table */}
          <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
            <h2 className="mb-3.5 text-[15px] font-semibold">Behavior metrics compared</h2>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[860px] border-collapse">
                <thead>
                  <tr>
                    {[
                      "Company",
                      "30d change",
                      "Avg daily Δ",
                      "Max gain",
                      "Max loss",
                      "Avg volume",
                      "Anomalies",
                      "In news",
                      "Pressure mix",
                    ].map((h) => (
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
                  {ranked.map(({ row, quoteChange, avgVolume, anomalies, pressure, inNews }) => {
                    const trend = row.summary?.price_trend;
                    const pressureStr =
                      Object.keys(pressure).length > 0
                        ? Object.entries(pressure)
                            .map(([k, n]) => `${k.replace(/_/g, " ")}×${n}`)
                            .join(", ")
                        : "—";
                    return (
                      <tr key={row.company.id} className="transition hover:bg-[#1a1f29]">
                        <td className="border-b border-[#1e222c] px-2.5 py-2.5">
                          <Link
                            to={`/companies/${row.company.id}`}
                            className="text-sm font-semibold hover:text-accent hover:underline"
                          >
                            {row.company.symbol}
                          </Link>
                          <span className="ml-1.5 hidden text-xs text-muted lg:inline">
                            {row.company.name}
                          </span>
                        </td>
                        <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm">
                          <ChangeBadge pct={quoteChange} />
                        </td>
                        <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums text-muted">
                          {trend ? `${trend.avg_daily_change >= 0 ? "+" : ""}${trend.avg_daily_change}%` : "—"}
                        </td>
                        <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums text-positive">
                          {trend ? `+${trend.max_daily_gain}%` : "—"}
                        </td>
                        <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums text-negative">
                          {trend ? `${trend.max_daily_loss}%` : "—"}
                        </td>
                        <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums">
                          {avgVolume ? avgVolume.toLocaleString() : "—"}
                        </td>
                        <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm">
                          {anomalies > 0 ? (
                            <span className="rounded-full bg-accent-2/15 px-2 py-0.5 text-xs font-medium text-accent-2">
                              {anomalies} day(s)
                            </span>
                          ) : (
                            <span className="text-muted">None</span>
                          )}
                        </td>
                        <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums">
                          {inNews}
                        </td>
                        <td className="max-w-[240px] border-b border-[#1e222c] px-2.5 py-2.5 text-xs capitalize text-muted">
                          {pressureStr}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-muted">
              Metrics computed server-side from crawled daily OHLCV data
              (<code className="bg-[#1e222c] px-1 rounded">/behavior-summary</code>) and
              categorized news counts (<code className="bg-[#1e222c] px-1 rounded">/api/news</code>).
            </p>
          </section>
        </>
      )}
    </div>
  );
}
