import type { ReactNode } from "react";
import type { NewsArticle } from "../types";

function timeAgo(iso: string): string {
  const hrs = Math.round((Date.now() - new Date(iso).getTime()) / 3600000);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.round(hrs / 24)}d ago`;
}

const sentimentClass: Record<NewsArticle["sentiment"], string> = {
  positive: "text-positive",
  negative: "text-negative",
  neutral: "text-muted",
};

interface NewsItemProps {
  item: NewsArticle;
  /** Fallback symbols shown when the article has no categorizations. */
  companyNames?: (string | undefined)[];
  children?: ReactNode;
}

export default function NewsItem({ item, companyNames = [], children }: NewsItemProps) {
  return (
    <div className="flex justify-between items-start gap-4 pb-3.5 border-b border-[#1e222c] last:border-b-0 last:pb-0">
      <div>
        <div className="mb-1 font-medium">
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-accent hover:underline"
            title={item.headline}
          >
            {item.headline}
          </a>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-muted">
          <span>{item.source}</span>
          <span className="opacity-50">•</span>
          <span>{timeAgo(item.publishedAt)}</span>
          <span className="opacity-50">•</span>
          <span className={sentimentClass[item.sentiment]}>{item.sentiment}</span>
        </div>
        <div className="flex flex-wrap gap-1.5 mt-2">
          {item.categorizations && item.categorizations.length > 0 ? (
            item.categorizations.map((c) => (
              <span
                key={c.companyId}
                className="bg-[#1e2430] border border-panel-border px-2.5 py-1 rounded-full text-[11px] text-muted flex items-center gap-1.5"
                title={`Method: ${c.method} | Confidence: ${Math.round(c.confidence * 100)}%`}
              >
                <span className="font-semibold text-[#e7e9ee]">{c.companySymbol || c.companyId}</span>
                <span className="opacity-40">|</span>
                <span className="text-[10px] text-accent-2 font-medium">{Math.round(c.confidence * 100)}%</span>
                <span className="text-[10px] text-muted italic">({c.method})</span>
                {c.isManual && (
                  <>
                    <span className="opacity-40">|</span>
                    <span className="text-[9px] text-accent font-semibold uppercase tracking-wider">Corrected</span>
                  </>
                )}
              </span>
            ))
          ) : (
            companyNames.map((name) => (
              <span
                key={name}
                className="bg-[#1e2430] border border-panel-border px-2.5 py-0.5 rounded-full text-[11px] text-muted"
              >
                {name}
              </span>
            ))
          )}
          {(!item.categorizations || item.categorizations.length === 0) && (
            <span className="bg-[#1e2430] border border-panel-border px-2.5 py-0.5 rounded-full text-[11px] text-accent-2">
              confidence {Math.round(item.confidence * 100)}%
            </span>
          )}
          {item.corrected && (!item.categorizations || item.categorizations.length === 0) && (
            <span className="bg-[#1e2430] border border-panel-border px-2.5 py-0.5 rounded-full text-[11px] text-accent">
              corrected
            </span>
          )}
        </div>
      </div>
      {children && <div className="shrink-0">{children}</div>}
    </div>
  );
}
