import {
  fetchCompanies,
  fetchDailyPrices,
  fetchBehaviorSummaryOrNull,
} from "./mappers";
import type {
  ApiCompany,
  ApiDailyPrice,
  BehaviorSummaryData,
  DailyAnalysis,
} from "./mappers";
import type { PricePoint } from "../types";

export interface CompanyMarketRow {
  company: ApiCompany;
  summary: BehaviorSummaryData | null;
  prices: PricePoint[];
}

export interface MarketOverview {
  companies: ApiCompany[];
  rows: CompanyMarketRow[];
}

function toPricePoints(
  prices: ApiDailyPrice[],
  anomalies: DailyAnalysis[] | undefined,
): PricePoint[] {
  const anomalyDates = new Set(
    (anomalies ?? []).map((d) => d.date.split("T")[0]),
  );
  return prices.map((p) => {
    const dateStr = p.date.split("T")[0];
    return {
      date: dateStr,
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
      anomaly: anomalyDates.has(dateStr),
    };
  });
}

/** Latest day-over-day % change from the behavior summary. */
export function latestChangePct(row: CompanyMarketRow): number | null {
  const recent = row.summary?.recent_days;
  if (recent && recent.length > 0) {
    return Number(recent[recent.length - 1].price_change_pct);
  }
  const prices = row.prices;
  if (prices.length >= 2) {
    const prev = prices[prices.length - 2].close;
    const last = prices[prices.length - 1].close;
    if (prev > 0) return ((last - prev) / prev) * 100;
  }
  return null;
}

/** Latest OHLCV snapshot for a company row, or null when no data exists. */
export function latestQuote(row: CompanyMarketRow):
  | {
      price: number;
      changePct: number | null;
      volume: number;
      turnover: number;
      date: string;
    }
  | null {
  if (row.prices.length === 0) return null;
  const last = row.prices[row.prices.length - 1];
  return {
    price: last.close,
    changePct: latestChangePct(row),
    volume: last.volume,
    turnover: last.turnover,
    date: last.date,
  };
}

/**
 * Companies + per-company 30d prices and behavior summaries in parallel.
 * Summaries are best-effort (null when the backend has insufficient data).
 */
export async function fetchMarketOverview(): Promise<MarketOverview> {
  const companies = await fetchCompanies();

  const rows = await Promise.all(
    companies.map(async (company): Promise<CompanyMarketRow> => {
      const [summary, rawPrices] = await Promise.all([
        fetchBehaviorSummaryOrNull(company.id, 30),
        fetchDailyPrices(company.id, 30).catch(() => [] as ApiDailyPrice[]),
      ]);
      return {
        company,
        summary,
        prices: toPricePoints(rawPrices, summary?.anomalies?.details),
      };
    }),
  );

  return { companies, rows };
}
