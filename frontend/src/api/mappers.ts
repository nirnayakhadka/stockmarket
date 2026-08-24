import type { NewsArticle } from "../types";
import { apiGet, apiPost, API_BASE_URL } from "./client";

export interface ApiCompany {
  id: number;
  symbol: string;
  name: string;
  sector: string | null;
  listed_date?: string | null;
}

export interface ApiCategorization {
  id: number;
  article_id: number;
  company_id: number;
  confidence_score: number;
  method: string;
  is_manual_correction: boolean;
  corrected_at: string | null;
}

export interface ApiArticle {
  id: number;
  headline: string;
  body_text: string;
  url: string;
  source_portal: string;
  published_at: string | null;
  crawled_at: string;
  categorizations: ApiCategorization[];
}

export function mapArticle(
  item: ApiArticle,
  companies: ApiCompany[],
): NewsArticle {
  const cats = item.categorizations ?? [];
  return {
    id: item.id,
    headline: item.headline,
    source: item.source_portal,
    url: item.url,
    publishedAt: item.published_at || item.crawled_at,
    companyIds: cats.map((c) => String(c.company_id)),
    confidence:
      cats.length > 0
        ? Math.max(...cats.map((c) => Number(c.confidence_score)))
        : 0,
    sentiment: "neutral",
    corrected: cats.some((c) => c.is_manual_correction),
    correctionHistory: [],
    categorizations: cats.map((c) => {
      const matched = companies.find((co) => co.id === c.company_id);
      return {
        companyId: String(c.company_id),
        companySymbol: matched?.symbol ?? `Co ${c.company_id}`,
        confidence: Number(c.confidence_score),
        method: c.method,
        isManual: c.is_manual_correction,
      };
    }),
  };
}

export function fetchCompanies(): Promise<ApiCompany[]> {
  return apiGet<ApiCompany[]>("/api/companies");
}

export function fetchNews(params: {
  companyId?: number;
  limit?: number;
}): Promise<ApiArticle[]> {
  const search = new URLSearchParams();
  if (params.companyId !== undefined)
    search.set("company_id", String(params.companyId));
  if (params.limit !== undefined) search.set("limit", String(params.limit));
  const qs = search.toString();
  return apiGet<ApiArticle[]>(`/api/news${qs ? `?${qs}` : ""}`);
}

export function recategorizeArticle(
  articleId: number,
  companyIds: number[],
  confidenceScore = 1.0,
): Promise<{ message: string; article_id: number }> {
  return apiPost(`/api/categorization/recategorize/${articleId}`, {
    company_ids: companyIds,
    confidence_score: confidenceScore,
  });
}

export interface BehaviorSummaryData {
  company: string;
  company_id: number;
  data_points: number;
  current_price?: number;
  vwap?: number | null;
  vwap_vs_close?: number | null;
  price_trend?: {
    total_change_pct: number;
    avg_daily_change: number;
    max_daily_gain: number;
    max_daily_loss: number;
  };
  volume_trend?: {
    avg_volume: number;
    max_volume: number;
    min_volume: number;
  };
  anomalies?: { count: number; details: DailyAnalysis[] };
  pressure_summary?: Record<string, number>;
  recent_days?: DailyAnalysis[];
}

export interface DailyAnalysis {
  date: string;
  close: number;
  volume: number;
  price_change_pct: number;
  volume_change_pct: number;
  pressure: string;
  pressure_score: number;
  is_volume_anomaly: boolean;
  volume_z_score: number | null;
}

export function fetchBehaviorSummary(
  companyId: number,
  rangeDays = 30,
): Promise<BehaviorSummaryData> {
  return apiGet<BehaviorSummaryData>(
    `/api/companies/${companyId}/behavior-summary?range_days=${rangeDays}`,
  );
}

export interface NewsPriceCorrelationRow {
  date: string | null;
  news_count: number;
  next_day_return: number | null;
  next_2_day_return?: number | null;
}

export interface NewsPriceCorrelationData {
  company?: string;
  data_points?: number;
  total_categorized_articles?: number;
  correlation?: NewsPriceCorrelationRow[];
  correlation_coefficient_news_vs_next_day_return?: number | null;
  note?: string;
  message?: string;
}

/** Best-effort; returns null when backend reports insufficient data. */
export async function fetchNewsPriceCorrelationOrNull(
  companyId: number,
  rangeDays = 30,
): Promise<NewsPriceCorrelationData | null> {
  try {
    const data = await apiGet<NewsPriceCorrelationData>(
      `/api/companies/${companyId}/news-price-correlation?range_days=${rangeDays}`,
    );
    if (data && data.message) return null;
    return data;
  } catch {
    return null;
  }
}

export interface ApiDailyPrice {
  id: number;
  company_id: number;
  date: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
  volume: number;
  turnover: number | null;
}

export function fetchDailyPrices(
  companyId: number,
  rangeDays = 30,
): Promise<ApiDailyPrice[]> {
  return apiGet<ApiDailyPrice[]>(
    `/api/companies/${companyId}/prices?range_days=${rangeDays}`,
  );
}

/** Best-effort fetch that returns null instead of throwing (e.g. insufficient data). */
export async function fetchBehaviorSummaryOrNull(
  companyId: number,
  rangeDays = 30,
): Promise<BehaviorSummaryData | null> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/api/companies/${companyId}/behavior-summary?range_days=${rangeDays}`,
    );
    if (!res.ok) return null;
    const data = await res.json();
    if (data && data.message) return null; // "Insufficient data" response
    return data as BehaviorSummaryData;
  } catch {
    return null;
  }
}

export interface ApiFloorsheetTransaction {
  id: number;
  buyer_broker: string;
  seller_broker: string;
  quantity: number;
  rate: number;
  amount: number | null;
}

export interface ApiFloorsheetResponse {
  company_id: number;
  symbol: string;
  date: string;
  transaction_count: number;
  transactions: ApiFloorsheetTransaction[];
}

export function fetchFloorsheet(
  companyId: number,
  date?: string,
): Promise<ApiFloorsheetResponse> {
  const qs = date ? `?date=${date}` : "";
  return apiGet<ApiFloorsheetResponse>(
    `/api/companies/${companyId}/floorsheet${qs}`,
  );
}

export interface MarketDataCollectResult {
  prices:
    | { inserted: number; updated: number; skipped: number; matched: number }
    | { error: string };
  floorsheet?:
    | { inserted: number; skipped_duplicate: number; matched: number }
    | { error: string };
}

export function triggerMarketDataCollection(
  includeFloorsheet = true,
): Promise<MarketDataCollectResult> {
  return apiPost<MarketDataCollectResult>(
    `/api/admin/market-data/collect-sync?include_floorsheet=${includeFloorsheet}`,
  );
}
