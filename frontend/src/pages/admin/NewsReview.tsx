import { useState } from "react";
import NewsItem from "../../components/NewsItem";
import { LoadingState, ErrorState, EmptyState } from "../../components/States";
import { useAsync } from "../../hooks/useAsync";
import {
  fetchCompanies,
  fetchNews,
  mapArticle,
  recategorizeArticle,
} from "../../api/mappers";
import type { ApiCompany } from "../../api/mappers";
import type { NewsArticle } from "../../types";

async function loadQueue(): Promise<{
  items: NewsArticle[];
  companies: ApiCompany[];
}> {
  const companiesData = await fetchCompanies();
  const newsData = await fetchNews({ limit: 200 });
  return {
    items: newsData.map((item) => mapArticle(item, companiesData)),
    companies: companiesData,
  };
}

export default function NewsReview() {
  const { data, loading, error, reload } = useAsync(loadQueue);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [pendingCompanyIds, setPendingCompanyIds] = useState<string[]>([]);
  const [savingId, setSavingId] = useState<number | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);

  if (loading) return <LoadingState label="Loading articles for review…" />;
  if (error)
    return <ErrorState title="Could not load review queue" message={error} onRetry={reload} />;
  if (!data) return null;

  const { items, companies } = data;

  function startEdit(item: NewsArticle) {
    setEditingId(item.id);
    setPendingCompanyIds(item.companyIds);
    setSaveError(null);
  }

  function toggleCompany(id: string) {
    setPendingCompanyIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    );
  }

  async function saveCorrection(item: NewsArticle) {
    setSavingId(item.id);
    setSaveError(null);
    try {
      // Persist to backend: replaces all existing tags with the selection
      await recategorizeArticle(item.id, pendingCompanyIds.map(Number), 1.0);
      reload();
      setEditingId(null);
    } catch (err: unknown) {
      setSaveError(err instanceof Error ? err.message : "Failed to save changes.");
    } finally {
      setSavingId(null);
    }
  }

  const manualCount = items.filter((i) => i.corrected).length;

  return (
    <div>
      <header className="mb-5.5">
        <h1 className="text-[22px] font-semibold">News review</h1>
        <p className="mt-1 text-sm text-muted">
          Correct mis-tagged articles — corrections are saved directly to the
          database and flagged as manual.
        </p>
        <p className="mt-1 text-xs text-muted">
          {items.length} article(s) · {manualCount} manually corrected
        </p>
      </header>

      {items.length === 0 ? (
        <EmptyState
          title="No articles in the queue"
          hint="Trigger a crawl run first — crawled articles are auto-tagged and appear here."
        />
      ) : (
        <section className="rounded-xl border border-panel-border bg-panel px-5 py-4.5">
          <ul className="flex flex-col gap-1">
            {items.map((item) => (
              <li key={item.id} className="py-2">
                <NewsItem item={item}>
                  {editingId === item.id ? (
                    <div className="flex w-[300px] max-w-full flex-col gap-2 rounded-lg border border-panel-border bg-[#171b24] p-3 sm:w-[380px]">
                      <span className="mb-1 text-xs font-medium text-muted">
                        Select associated companies:
                      </span>
                      <div className="grid max-h-[180px] grid-cols-2 gap-1.5 overflow-y-auto pr-1">
                        {companies.map((c) => (
                          <label
                            key={c.id}
                            className="flex cursor-pointer items-center gap-2 rounded-lg border border-panel-border bg-[#1e2430] px-2 py-1.5 text-[11px] hover:bg-[#262d3b]"
                          >
                            <input
                              type="checkbox"
                              className="accent-accent"
                              checked={pendingCompanyIds.includes(String(c.id))}
                              onChange={() => toggleCompany(String(c.id))}
                            />
                            <span className="font-semibold text-white">{c.symbol}</span>
                          </label>
                        ))}
                      </div>
                      {saveError && editingId === item.id && (
                        <p className="text-xs text-negative">{saveError}</p>
                      )}
                      <div className="mt-2 flex justify-end gap-2 border-t border-panel-border pt-2">
                        <button
                          className="rounded-lg border border-panel-border px-3 py-1.5 text-xs text-muted transition hover:bg-[#262d3b] hover:text-white disabled:opacity-50"
                          onClick={() => setEditingId(null)}
                          disabled={savingId === item.id}
                        >
                          Cancel
                        </button>
                        <button
                          className="flex items-center gap-1 rounded-lg bg-accent px-3.5 py-1.5 text-xs font-semibold text-[#0c0e13] transition hover:bg-[#6fe0d5] disabled:opacity-50"
                          onClick={() => saveCorrection(item)}
                          disabled={savingId === item.id}
                        >
                          {savingId === item.id ? "Saving…" : "Save tags"}
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      className="rounded-lg border border-panel-border bg-[#1e2430] px-2.5 py-1.5 text-xs font-medium transition hover:bg-[#262d3b] hover:text-white"
                      onClick={() => startEdit(item)}
                    >
                      Correct tags
                    </button>
                  )}
                </NewsItem>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
