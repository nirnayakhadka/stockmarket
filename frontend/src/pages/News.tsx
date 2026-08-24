import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import NewsItem from "../components/NewsItem";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { fetchCompanies, fetchNews, mapArticle } from "../api/mappers";
import type { ApiCompany } from "../api/mappers";
import type { NewsArticle } from "../types";

const PAGE_SIZE = 20;

async function loadNewsFeed(): Promise<{ articles: NewsArticle[]; companies: ApiCompany[] }> {
  const companies = await fetchCompanies();
  const raw = await fetchNews({ limit: 500 });
  return { articles: raw.map((a) => mapArticle(a, companies)), companies };
}

export default function News() {
  const { data, loading, error, reload } = useAsync(loadNewsFeed);
  const [companyId, setCompanyId] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [visible, setVisible] = useState(PAGE_SIZE);

  const filtered = useMemo(() => {
    const list = data?.articles ?? [];
    const q = query.trim().toLowerCase();
    return list.filter((a) => {
      if (companyId !== "all" && !a.companyIds.includes(companyId)) return false;
      if (q && !a.headline.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [data, companyId, query]);

  const shown = filtered.slice(0, visible);
  // Reset paging whenever filters change
  const resetPaging = () => setVisible(PAGE_SIZE);

  if (loading) return <LoadingState label="Loading news feed…" />;
  if (error)
    return <ErrorState title="Could not load news" message={error} onRetry={reload} />;
  if (!data) return null;

  return (
    <div>
      <header className="mb-5.5">
        <h1 className="text-[22px] font-semibold">Market news</h1>
        <p className="mt-1 text-sm text-muted">
          Articles crawled from merolagani, sharesansar, nepsealpha and bizmandu —
          tagged to companies automatically and correctable by analysts.
        </p>
      </header>

      <div className="mb-5 flex flex-wrap items-center gap-2.5">
        <input
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            resetPaging();
          }}
          placeholder="Search headlines…"
          className="w-60 rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent/50"
        />
        <select
          value={companyId}
          onChange={(e) => {
            setCompanyId(e.target.value);
            resetPaging();
          }}
          className="rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none focus:border-accent/50"
          aria-label="Filter by company"
        >
          <option value="all">All companies</option>
          {data.companies.map((c) => (
            <option key={c.id} value={String(c.id)}>
              {c.symbol} — {c.name}
            </option>
          ))}
        </select>
        <span className="text-xs text-muted">
          {filtered.length} article(s)
        </span>
      </div>

      {shown.length === 0 ? (
        <EmptyState
          title="No articles found"
          hint="Try a different company or clear the search — or trigger a crawl from the admin panel."
          action={
            <Link
              to="/companies"
              className="rounded-lg border border-panel-border bg-[#1e2430] px-3 py-1.5 text-xs font-medium hover:bg-[#262d3b]"
            >
              Browse companies
            </Link>
          }
        />
      ) : (
        <>
          <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
            <ul className="flex flex-col gap-1">
              {shown.map((item) => (
                <li key={item.id} className="py-2">
                  <NewsItem item={item} />
                </li>
              ))}
            </ul>
          </section>
          {visible < filtered.length && (
            <div className="mt-5 text-center">
              <button
                onClick={() => setVisible((v) => v + PAGE_SIZE)}
                className="rounded-lg border border-panel-border bg-[#1e2430] px-4 py-2 text-sm font-medium transition hover:bg-[#262d3b]"
              >
                Load more ({filtered.length - visible} remaining)
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
