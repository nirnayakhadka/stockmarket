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
import { fetchMarketQuotes } from "../api/market";
import type { MarketQuoteRow } from "../api/market";
import { fetchCompanies, fetchNews, mapArticle } from "../api/mappers";

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

const MAX_CHART_SERIES = 10;

interface RowMetrics {
  row: MarketQuoteRow;
  totalChangePct: number | null;
  avgDailyChange: number | null;
  maxGain: number | null;
  maxLoss: number | null;
  avgVolume: number;
  inNews: number;
}

async function loadAnalysis(): Promise<{
  rows: MarketQuoteRow[];
  metrics: RowMetrics[];
  newsCounts: Record<number, number>;
}> {
  const [quotesRes, companies, raw] = await Promise.all([
    fetchMarketQuotes(),
    fetchCompanies(),
    fetchNews({ limit: 500 }),
  ]);
  const articles = raw.map((a) => mapArticle(a, companies));
  const newsCounts: Record<number, number> = {};
  for (const article of articles) {
    for (const cid of article.companyIds) {
      const id = Number(cid);
      newsCounts[id] = (newsCounts[id] ?? 0) + 1;
    }
  }

  const metrics = quotesRes.quotes.map((row) => {
    const hist = row.history;
    let totalChangePct: number | null = null;
    let avgDailyChange: number | null = null;
    let maxGain: number | null = null;
    let maxLoss: number | null = null;
    if (hist.length >= 2) {
      const base = hist[0].close || 1;
      totalChangePct = ((hist[hist.length - 1].close - base) / base) * 100;
      const daily: number[] = [];
      for (let i = 1; i < hist.length; i++) {
        const prev = hist[i - 1].close;
        if (prev > 0)
          daily.push(((hist[i].close - prev) / prev) * 100);
      }
      if (daily.length > 0) {
        avgDailyChange = daily.reduce((s, v) => s + v, 0) / daily.length;
        maxGain = Math.max(...daily);
        maxLoss = Math.min(...daily);
      }
    }
    const avgVolume =
      hist.length > 0
        ? Math.round(hist.reduce((s, h) => s + h.volume, 0) / hist.length)
        : 0;
    return {
      row,
      totalChangePct,
      avgDailyChange,
      maxGain,
      maxLoss,
      avgVolume,
      inNews: newsCounts[row.company_id] ?? 0,
    };
  });

  return { rows: quotesRes.quotes, metrics, newsCounts };
}

export default function Analysis() {
  const { data, loading, error, reload } = useAsync(loadAnalysis);

  // Comparison chart limited to the busiest names — 240 lines are unreadable.
  const series = useMemo(() => {
    const top = [...(data?.metrics ?? [])]
      .sort((a, b) => b.avgVolume - a.avgVolume)
      .slice(0, MAX_CHART_SERIES)
      .map((m) => m.row);
    return top
      .filter((r) => r.history.length >= 2)
      .map((r) => {
        const base = r.history[0].close || 1;
        return {
          symbol: r.symbol,
          companyId: r.company_id,
          points: r.history.map((h) => ({
            date: h.date,
            pct: Number((((h.close - base) / base) * 100).toFixed(2)),
          })),
        };
      });
  }, [data]);

  const chartData = useMemo(() => {
    const byDate = new Map<string, Record<string, number>>();
    series.forEach(({ symbol, points }) => {
      points.forEach((p) => {
        const rowMap = byDate.get(p.date) ?? {};
        rowMap[symbol] = p.pct;
        byDate.set(p.date, rowMap);
      });
    });
    return Array.from(byDate.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([date, values]) => ({ date, ...values }));
  }, [series]);

  const ranked = useMemo(
    () =>
      [...(data?.metrics ?? [])]
        .filter((m) => m.row.quote !== null || m.row.history.length > 0)
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
    .filter((r) => r.totalChangePct !== null)
    .sort((a, b) => (b.totalChangePct ?? 0) - (a.totalChangePct ?? 0))[0];
  const worstPerformer = [...ranked]
    .filter((r) => r.totalChangePct !== null)
    .sort((a, b) => (a.totalChangePct ?? 0) - (b.totalChangePct ?? 0))[0];
  const mostInNews = [...ranked].sort((a, b) => b.inNews - a.inNews)[0];

  return (
    <div>
      <header className="mb-5.5">
        <h1 className="text-[22px] font-semibold">Analysis — cross-company comparison</h1>
        <p className="mt-1 text-sm text-muted">
          Side-by-side behavior of every listed company over the last 30 days,
          computed from the synced NEPSE feed.
        </p>
      </header>

      {ranked.length === 0 ? (
        <EmptyState
          title="No analysis data"
          hint="The backend syncs prices automatically at startup and on a schedule — reload once data has arrived."
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
                  ? `${bestPerformer.row.symbol} ${bestPerformer.totalChangePct! >= 0 ? "+" : ""}${bestPerformer.totalChangePct!.toFixed(2)}%`
                  : "—"
              }
              tone={bestPerformer && bestPerformer.totalChangePct! >= 0 ? "positive" : "negative"}
            />
            <StatCard
              label="Worst performer (30d)"
              value={
                worstPerformer
                  ? `${worstPerformer.row.symbol} ${worstPerformer.totalChangePct! >= 0 ? "+" : ""}${worstPerformer.totalChangePct!.toFixed(2)}%`
                  : "—"
              }
              tone={worstPerformer && worstPerformer.totalChangePct! >= 0 ? "positive" : "negative"}
            />
            <StatCard
              label="Most active (avg vol)"
              value={ranked[0]?.row.symbol ?? "—"}
              sublabel={ranked[0] ? ranked[0].avgVolume.toLocaleString() : undefined}
            />
            <StatCard
              label="Most in news (30d)"
              value={mostInNews && mostInNews.inNews > 0 ? `${mostInNews.row.symbol} (${mostInNews.inNews})` : "—"}
            />
          </section>

          {/* Normalized performance */}
          <section className="mb-5 rounded-xl border border-panel-border bg-panel px-5 py-4.5">
            <h2 className="mb-1 text-[15px] font-semibold">
              Cumulative % change — last 30 days
            </h2>
            <p className="mb-3.5 text-xs text-muted">
              Top {MAX_CHART_SERIES} most-active companies rebased to 0% at the start of the window.
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
                  {series.map(({ symbol }, i) => (
                    <Line
                      key={symbol}
                      type="monotone"
                      dataKey={symbol}
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
                hint="At least two days of synced prices per company are required for the comparison chart."
              />
            )}
          </section>

          {/* Avg volume comparison */}
          <section className="mb-5 rounded-xl border border-panel-border bg-panel px-5 py-4.5">
            <h2 className="mb-3.5 text-[15px] font-semibold">Average daily volume</h2>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={ranked.slice(0, 15).map((r) => ({
                  symbol: r.row.symbol,
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
              <table className="w-full min-w-[760px] border-collapse">
                <thead>
                  <tr>
                    {[
                      "Company",
                      "30d change",
                      "Avg daily Δ",
                      "Max gain",
                      "Max loss",
                      "Avg volume",
                      "Latest price",
                      "In news",
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
                  {ranked.map((m) => (
                    <tr key={m.row.company_id} className="transition hover:bg-[#1a1f29]">
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5">
                        <Link
                          to={`/companies/${m.row.company_id}`}
                          className="text-sm font-semibold hover:text-accent hover:underline"
                        >
                          {m.row.symbol}
                        </Link>
                        <span className="ml-1.5 hidden text-xs text-muted lg:inline">
                          {m.row.name}
                        </span>
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm">
                        <ChangeBadge pct={m.totalChangePct} />
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums text-muted">
                        {m.avgDailyChange !== null
                          ? `${m.avgDailyChange >= 0 ? "+" : ""}${m.avgDailyChange.toFixed(2)}%`
                          : "—"}
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums text-positive">
                        {m.maxGain !== null ? `+${m.maxGain.toFixed(2)}%` : "—"}
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums text-negative">
                        {m.maxLoss !== null ? `${m.maxLoss.toFixed(2)}%` : "—"}
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums">
                        {m.avgVolume ? m.avgVolume.toLocaleString() : "—"}
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums">
                        {m.row.quote ? `Rs ${m.row.quote.price.toFixed(2)}` : "—"}
                      </td>
                      <td className="border-b border-[#1e222c] px-2.5 py-2.5 text-sm tabular-nums">
                        {m.inNews}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs text-muted">
              Metrics computed from the live NEPSE sync stored by the backend
              (<code className="bg-[#1e222c] px-1 rounded">/api/market/quotes</code>) and
              categorized news counts (<code className="bg-[#1e222c] px-1 rounded">/api/news</code>).
            </p>
          </section>
        </>
      )}
    </div>
  );
}
