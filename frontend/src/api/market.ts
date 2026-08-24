import { apiGet } from "./client";
import type { PricePoint } from "../types";
import type { ApiDailyPrice } from "./mappers";

// ---------------------------------------------------------------------------
// Live market data - served by the backend from its synced NEPSE tables
// (see backend app/routers/market.py). No dummy data anywhere.
// ---------------------------------------------------------------------------

export interface QuoteData {
  price: number;
  open: number;
  high: number;
  low: number;
  prev_close: number | null;
  point_change: number | null;
  change_pct: number | null;
  volume: number;
  turnover: number | null;
  transactions: number;
  date: string;
}

export interface MarketQuoteRow {
  company_id: number;
  symbol: string;
  name: string;
  sector: string | null;
  quote: QuoteData | null;
  /** Recent daily history (oldest first) for sparklines / comparison charts. */
  history: { date: string; close: number; volume: number }[];
}

export interface MarketQuotesResponse {
  count: number;
  quotes: MarketQuoteRow[];
}

/** GET /api/market/quotes - every listed company in one request. */
export async function fetchMarketQuotes(
  sparklineDays = 30,
): Promise<MarketQuotesResponse> {
  return apiGet<MarketQuotesResponse>(
    `/api/market/quotes?sparkline_days=${sparklineDays}`,
  );
}

export interface IndexSnapshot {
  index_name: string;
  value: number | null;
  point_change: number | null;
  pct_change: number | null;
  open: number | null;
  high: number | null;
  low: number | null;
  prev_close: number | null;
  turnover: number | null;
  ceil: number | null;
  floor: number | null;
  business_date: string;
  captured_at: string | null;
}

export interface IndicesResponse {
  indices: IndexSnapshot[];
  history: Record<string, IndexSnapshot[]>;
}

/** GET /api/market/indices - latest snapshot of every NEPSE index (+history). */
export function fetchMarketIndices(historyDays = 90): Promise<IndicesResponse> {
  return apiGet<IndicesResponse>(`/api/market/indices?history_days=${historyDays}`);
}

export interface MarketStatusResponse {
  is_open: boolean;
  is_open_raw?: string | null;
  as_of?: string | null;
  updated_at: string | null;
}

/** GET /api/market/status - official market open/closed flag. */
export function fetchMarketStatus(): Promise<MarketStatusResponse> {
  return apiGet<MarketStatusResponse>("/api/market/status");
}

export interface ScripStat {
  company_id: number;
  symbol: string;
  name: string;
  price: number;
  prev_close: number | null;
  point_change: number | null;
  change_pct: number | null;
  volume: number;
  turnover: number | null;
}

export interface MarketSummaryResponse {
  status: { is_open: boolean; updated_at: string | null };
  trade_date: string | null;
  indices: IndexSnapshot[];
  breadth: {
    advancers: number;
    decliners: number;
    unchanged: number;
    total_turnover: number;
    total_volume: number;
  };
  gainers: ScripStat[];
  losers: ScripStat[];
  turnover_leaders: ScripStat[];
  volume_leaders: ScripStat[];
  official_top_turnover_scrips: {
    symbol: string;
    ltp: number | null;
    pct_change: number | null;
    amount: number | null;
    rank: number;
    business_date: string;
  }[];
}

/** GET /api/market/summary - dashboard payload (indices + movers + breadth). */
export function fetchMarketSummary(): Promise<MarketSummaryResponse> {
  return apiGet<MarketSummaryResponse>("/api/market/summary");
}

export interface NewsBulletin {
  id: number;
  title: string;
  published_on: string | null;
  source_url: string | null;
}

/** GET /api/market/news-bulletins - official NEPSE announcements. */
export function fetchNewsBulletins(limit = 20): Promise<NewsBulletin[]> {
  return apiGet<NewsBulletin[]>(`/api/market/news-bulletins?limit=${limit}`);
}

// ---------------------------------------------------------------------------
// Back-compat helpers still used by per-company views.
// ---------------------------------------------------------------------------

export function toPricePoints(
  prices: ApiDailyPrice[],
): PricePoint[] {
  return prices.map((p) => ({
    date: p.date.split("T")[0],
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
  }));
}

/** Day-over-day % change from a quote row (null when no prev close yet). */
export function quoteChangePct(row: MarketQuoteRow): number | null {
  return row.quote?.change_pct ?? null;
}
