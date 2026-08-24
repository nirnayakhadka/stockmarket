import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from "recharts";
import PriceChart from "../components/PriceChart";
import NewsItem from "../components/NewsItem";
import StatCard from "../components/StatCard";
import FloorsheetTable from "../components/FloorsheetTable";
import ChangeBadge from "../components/ChangeBadge";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import {
  fetchCompanies,
  fetchDailyPrices,
  fetchBehaviorSummaryOrNull,
  fetchNewsPriceCorrelationOrNull,
  fetchNews,
  mapArticle,
} from "../api/mappers";
import type {
  ApiCompany,
  BehaviorSummaryData,
  DailyAnalysis,
  NewsPriceCorrelationData,
} from "../api/mappers";
import type { NewsArticle, PricePoint } from "../types";

export default function CompanyDetail() {
  const { id } = useParams<{ id: string }>();
  const [company, setCompany] = useState<ApiCompany | null>(null);
  const [prices, setPrices] = useState<PricePoint[]>([]);
  const [summary, setSummary] = useState<BehaviorSummaryData | null>(null);
  const [correlation, setCorrelation] = useState<NewsPriceCorrelationData | null>(null);
  const [news, setNews] = useState<NewsArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rangeDays, setRangeDays] = useState(30);

  useEffect(() => {
    if (!id) return;

    setLoading(true);
    setError(null);
    const companyId = Number(id);

    (async () => {
      try {
        const companiesData = await fetchCompanies();

        const companyData = companiesData.find((c) => c.id === companyId);
        if (!companyData) throw new Error("Company not found");
        setCompany(companyData);

        // Best-effort: page still renders if analysis data is unavailable
        const summaryData = await fetchBehaviorSummaryOrNull(companyId, rangeDays);
        setSummary(summaryData);
        setCorrelation(await fetchNewsPriceCorrelationOrNull(companyId, rangeDays));

        const pricesData = await fetchDailyPrices(companyId, rangeDays);
        const anomalyDates = new Set(
          summaryData?.anomalies?.details?.map((d: DailyAnalysis) => d.date.split("T")[0]) || [],
        );
        const mappedPrices: PricePoint[] = pricesData.map((p) => {
          const pDateStr = p.date.split("T")[0];
          return {
            date: pDateStr,
            open: Number(p.open_price),
            high: Number(p.high_price),
            low: Number(p.low_price),
            close: Number(p.close_price),
            volume: p.volume,
            turnover: p.turnover ? Number(p.turnover) : 0,
            vwap:
              (Number(p.open_price) +
                Number(p.high_price) +
                Number(p.low_price) +
                Number(p.close_price)) /
              4,
            anomaly: anomalyDates.has(pDateStr),
          };
        });
        setPrices(mappedPrices);

        const newsData = await fetchNews({ companyId, limit: 50 });
        setNews(newsData.map((item) => mapArticle(item, companiesData)));
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load company detail page");
      } finally {
        setLoading(false);
      }
    })();
  }, [id, rangeDays]);

  const latest = prices.length > 0 ? prices[prices.length - 1] : null;
  const prev = prices.length > 1 ? prices[prices.length - 2] : null;
  const dailyChangePct =
    latest && prev && prev.close > 0
      ? ((latest.close - prev.close) / prev.close) * 100
      : null;
  const priceChange = summary?.price_trend?.total_change_pct ?? null;
  const anomalyDaysCount = summary?.anomalies?.count ?? 0;
  const lastDay: DailyAnalysis | undefined =
    summary?.recent_days && summary.recent_days.length > 0
      ? summary.recent_days[summary.recent_days.length - 1]
      : undefined;

  if (loading)
    return <LoadingState label={`Loading ${company?.symbol ?? "company"}…`} />;

  if (error || !company)
    return (
      <div>
        <Link to="/companies" className="text-xs text-muted hover:text-white">
          ← Back to markets
        </Link>
        <div className="mt-4">
          <ErrorState message={error || "Company not found."} onRetry={() => window.location.reload()} />
        </div>
      </div>
    );

  return (
    <div>
      <header className="mb-5.5">
        <Link to="/companies" className="text-xs text-muted hover:text-white">
          ← Back to markets
        </Link>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-[22px] font-semibold">
              {company.symbol}
              <span className="ml-2 text-base font-normal text-muted">{company.name}</span>
            </h1>
            <div className="mt-1 flex items-center gap-3 text-sm">
              <span className="text-xl font-semibold tabular-nums">
                {latest ? `Rs ${latest.close.toFixed(2)}` : "—"}
              </span>
              <ChangeBadge pct={dailyChangePct} />
              <span className="rounded bg-[#1e2430] px-2 py-0.5 text-[11px] uppercase tracking-wide text-muted">
                {company.sector ?? "—"}
              </span>
            </div>
          </div>
          <label className="flex items-center gap-2 text-xs text-muted">
            Range
            <select
              value={rangeDays}
              onChange={(e) => setRangeDays(Number(e.target.value))}
              className="rounded-lg border border-panel-border bg-[#1e2430] px-2.5 py-1.5 text-sm outline-none focus:border-accent/50"
            >
              <option value={7}>7 days</option>
              <option value={30}>30 days</option>
              <option value={90}>90 days</option>
            </select>
          </label>
        </div>
      </header>

      <section className="mb-5.5 grid grid-cols-2 gap-3.5 lg:grid-cols-4">
        <StatCard
          label="Last close"
          value={latest ? `Rs ${latest.close.toFixed(2)}` : "—"}
          sublabel={latest ? `as of ${latest.date}` : undefined}
        />
        <StatCard
          label={`Change (${rangeDays}d)`}
          value={<ChangeBadge pct={priceChange} />}
        />
        <StatCard
          label="Volume (last day)"
          value={latest ? latest.volume.toLocaleString() : "—"}
        />
        <StatCard
          label="Volume anomaly days"
          value={anomalyDaysCount}
          sublabel={anomalyDaysCount > 0 ? "z-score > 2.0" : undefined}
        />
      </section>

      <section className="mb-5 rounded-xl border border-panel-border bg-panel px-5 py-4.5">
        <h2 className="mb-3.5 text-[15px] font-semibold">
          Price &amp; volume — last {rangeDays} days
        </h2>
        {prices.length > 0 ? (
          <PriceChart data={prices} />
        ) : (
          <EmptyState
            title="No price history available"
            hint="Collect market data from the admin panel or run the seed scripts."
          />
        )}
      </section>

      {summary ? (
        <section className="mb-5 rounded-xl border border-panel-border bg-panel px-5 py-4.5">
          <h2 className="mb-3.5 text-[15px] font-semibold">Behavior analysis</h2>
          <div className="grid gap-4.5 sm:grid-cols-2 xl:grid-cols-4">
            <div>
              <div className="text-xs text-muted">Buy/sell pressure (latest day)</div>
              <PressureBadge pressure={lastDay?.pressure} score={lastDay?.pressure_score} />
            </div>
            <div>
              <div className="text-xs text-muted">VWAP vs close</div>
              <div className="mt-1 text-sm leading-relaxed text-white">
                VWAP:{" "}
                <span className="font-semibold tabular-nums">
                  Rs {summary.vwap != null ? Number(summary.vwap).toFixed(2) : "—"}
                </span>
                {summary.vwap_vs_close != null && (
                  <span
                    className={`mt-0.5 block text-xs ${
                      summary.vwap_vs_close >= 0 ? "text-positive" : "text-negative"
                    }`}
                  >
                    {summary.vwap_vs_close >= 0 ? "Below" : "Above"} close by{" "}
                    Rs {Math.abs(Number(summary.vwap_vs_close)).toFixed(2)}
                  </span>
                )}
              </div>
            </div>
            <div>
              <div className="text-xs text-muted">Avg daily volume</div>
              <div className="mt-1 text-sm leading-relaxed text-white tabular-nums">
                {summary.volume_trend ? summary.volume_trend.avg_volume.toLocaleString() : "—"}
                <span className="mt-0.5 block text-xs text-muted">
                  Range:{" "}
                  {summary.volume_trend
                    ? `${summary.volume_trend.min_volume.toLocaleString()} – ${summary.volume_trend.max_volume.toLocaleString()}`
                    : "—"}
                </span>
              </div>
            </div>
            <div>
              <div className="text-xs text-muted">Recent day moves</div>
              <ul className="mt-1 flex flex-col gap-1">
                {(summary.recent_days ?? []).slice(-3).reverse().map((d) => (
                  <li key={d.date} className="flex items-center justify-between gap-3 text-xs">
                    <span className="text-muted">{d.date.split("T")[0]}</span>
                    <ChangeBadge pct={d.price_change_pct} arrow={false} />
                  </li>
                ))}
                {(!summary.recent_days || summary.recent_days.length === 0) && (
                  <li className="text-xs text-muted">No recent analysis rows.</li>
                )}
              </ul>
            </div>
          </div>

          {/* News-price correlation */}
          <div className="mt-4 border-t border-panel-border pt-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-[13px] font-semibold">
                News volume vs next-day price move
              </h3>
              {correlation?.correlation_coefficient_news_vs_next_day_return !=
                null && (
                <span className="rounded-full border border-panel-border bg-[#1e2430] px-2.5 py-1 text-xs text-muted">
                  Pearson r (news vs next-day return):{" "}
                  <span className="font-semibold text-accent">
                    {correlation.correlation_coefficient_news_vs_next_day_return}
                  </span>
                </span>
              )}
            </div>
            {correlation &&
            correlation.correlation &&
            correlation.correlation.some((r) => r.news_count > 0) ? (
              <ResponsiveContainer width="100%" height={200}>
                <ComposedChart
                  data={correlation.correlation.map((r) => ({
                    date: r.date,
                    news_count: r.news_count,
                    nextDay: r.next_day_return,
                  }))}
                  margin={{ top: 6, right: 16, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} minTickGap={24} />
                  <YAxis yAxisId="news" tick={{ fontSize: 10 }} allowDecimals={false} width={32} />
                  <YAxis yAxisId="chg" orientation="right" tick={{ fontSize: 10 }} unit="%" width={48} />
                  <Tooltip contentStyle={{ background: "#1b1f27", border: "1px solid #333", fontSize: 12 }} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar yAxisId="news" dataKey="news_count" name="Articles" fill="#63b3ed" maxBarSize={18} />
                  <Line yAxisId="chg" type="monotone" dataKey="nextDay" name="Next-day return %" stroke="#f6ad55" dot={false} />
                </ComposedChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-sm italic text-muted">
                No tagged articles overlap the price window yet — correct article tags in
                News Review to build the news-price dataset.
              </p>
            )}
          </div>
        </section>
      ) : (
        <section className="mb-5 rounded-xl border border-panel-border bg-panel px-5 py-4.5">
          <h2 className="mb-2 text-[15px] font-semibold">Behavior analysis</h2>
          <p className="text-sm text-muted">
            Not enough price history yet to compute behavior metrics for this company.
          </p>
        </section>
      )}

      <FloorsheetTable companyId={Number(id)} />

      <section className="mb-5 rounded-xl border border-panel-border bg-panel px-5 py-4.5">
        <div className="mb-3.5 flex items-center justify-between">
          <h2 className="text-[15px] font-semibold">
            Categorized news for {company.symbol}
          </h2>
          <Link to="/news" className="text-xs text-accent hover:underline">
            All news →
          </Link>
        </div>
        <div className="flex flex-col gap-3.5">
          {news.length === 0 && (
            <EmptyState
              title={`No news tagged to ${company.symbol}`}
              hint="Articles are tagged automatically during categorization; reviewers can fix tags in News Review."
            />
          )}
          {news.map((item) => (
            <NewsItem key={item.id} item={item} />
          ))}
        </div>
      </section>
    </div>
  );
}

function PressureBadge({ pressure, score }: { pressure?: string; score?: number }) {
  const label = (pressure ?? "neutral")
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
  const tone =
    pressure?.includes("buy") || pressure === "strong_buy"
      ? "text-positive"
      : pressure?.includes("sell")
        ? "text-negative"
        : "text-muted";
  return (
    <div className={`mt-1 text-sm font-semibold ${tone}`}>
      {label}
      {score !== undefined && (
        <span className="ml-1.5 text-xs font-normal text-muted">(score: {score})</span>
      )}
    </div>
  );
}
