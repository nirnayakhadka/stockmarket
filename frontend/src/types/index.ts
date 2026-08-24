export type Role = "admin" | "analyst" | "viewer";

export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
}

export interface PricePoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  turnover: number;
  vwap: number;
  anomaly?: boolean;
}

export type Sentiment = "positive" | "negative" | "neutral";

export interface CorrectionRecord {
  at: string;
  from: string[];
  to: string[];
}

export interface NewsCategorization {
  companyId: string;
  companySymbol?: string;
  confidence: number;
  method: string;
  isManual: boolean;
}

export interface NewsArticle {
  id: number;
  headline: string;
  source: string;
  url: string;
  publishedAt: string;
  companyIds: string[];
  confidence: number;
  sentiment: Sentiment;
  corrected: boolean;
  correctionHistory: CorrectionRecord[];
  categorizations?: NewsCategorization[];
}

export type CrawlStatus = "completed" | "failed" | "running" | "pending";

export interface CrawlRun {
  id: string;
  startedAt: string;
  status: CrawlStatus;
  articlesFound: number;
  durationSec: number;
  error?: string;
}
