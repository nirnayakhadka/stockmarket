import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import ChangeBadge from "../components/ChangeBadge";
import Sparkline from "../components/Sparkline";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { useAsync } from "../hooks/useAsync";
import { fetchMarketQuotes, quoteChangePct } from "../api/market";
import type { MarketQuoteRow } from "../api/market";

type SortKey = "symbol" | "price" | "change" | "volume" | "turnover";

export default function Companies() {
  const { data, loading, error, reload } = useAsync(() =>
    fetchMarketQuotes().then((r) => r.quotes),
  );
  const [sector, setSector] = useState<string>("all");
  const [sortKey, setSortKey] = useState<SortKey>("symbol");
  const [query, setQuery] = useState("");

  const sectors = useMemo(() => {
    const set = new Set(
      (data ?? [])
        .map((r) => r.sector)
        .filter((s): s is string => Boolean(s)),
    );
    return ["all", ...Array.from(set).sort()];
  }, [data]);

  const rows = useMemo(() => {
    let list = data ?? [];
    if (sector !== "all")
      list = list.filter((r) => r.sector === sector);
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      list = list.filter(
        (r) =>
          r.symbol.toLowerCase().includes(q) ||
          r.name.toLowerCase().includes(q),
      );
    }

    return [...list].sort((a: MarketQuoteRow, b: MarketQuoteRow) => {
      switch (sortKey) {
        case "price":
          return (b.quote?.price ?? 0) - (a.quote?.price ?? 0);
        case "change":
          return (b.quote?.change_pct ?? -Infinity) -
            (a.quote?.change_pct ?? -Infinity);
        case "volume":
          return (b.quote?.volume ?? 0) - (a.quote?.volume ?? 0);
        case "turnover":
          return (b.quote?.turnover ?? 0) - (a.quote?.turnover ?? 0);
        default:
          return a.symbol.localeCompare(b.symbol);
      }
    });
  }, [data, sector, sortKey, query]);

  if (loading) return <LoadingState label="Loading companies…" />;
  if (error)
    return (
      <ErrorState title="Could not load companies" message={error} onRetry={reload} />
    );

  return (
    <div>
      <header className="mb-5.5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-semibold">Markets — listed companies</h1>
          <p className="mt-1 text-sm text-muted">
            {rows.length} companies synced from the official NEPSE feed with
            live OHLCV data.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search symbol or name…"
            className="w-52 rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none placeholder:text-muted focus:border-accent/50"
          />
          <select
            value={sector}
            onChange={(e) => setSector(e.target.value)}
            className="rounded-lg border border-panel-border bg-[#1e2430] px-3 py-2 text-sm outline-none focus:border-accent/50"
            aria-label="Filter by sector"
          >
            {sectors.map((s) => (
              <option key={s} value={s}>
                {s === "all" ? "All sectors" : s}
              </option>
            ))}
          </select>
        </div>
      </header>

      {rows.length === 0 ? (
        <EmptyState
          title="No companies match your filters"
          hint="Try clearing the search box or selecting another sector."
        />
      ) : (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map((row) => {
            const q = row.quote;
            return (
              <Link
                key={row.company_id}
                to={`/companies/${row.company_id}`}
                className="group rounded-xl border border-panel-border bg-panel px-5 py-4 transition hover:border-accent/40"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-base font-bold group-hover:text-accent">
                        {row.symbol}
                      </span>
                      <span className="rounded bg-[#1e2430] px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted">
                        {row.sector ?? "—"}
                      </span>
                    </div>
                    <div className="mt-0.5 line-clamp-1 max-w-[220px] text-xs text-muted">
                      {row.name}
                    </div>
                  </div>
                  <Sparkline values={row.history.map((h) => h.close)} height={40} />
                </div>
                <div className="mt-3.5 flex items-end justify-between">
                  <div>
                    <div className="text-xl font-semibold tabular-nums">
                      {q ? `Rs ${q.price.toFixed(2)}` : "—"}
                    </div>
                    <ChangeBadge pct={quoteChangePct(row)} className="text-xs" />
                  </div>
                  <div className="text-right text-xs text-muted">
                    <div>Vol {q ? q.volume.toLocaleString() : "—"}</div>
                    <div>
                      {q && q.transactions > 0
                        ? `${q.transactions.toLocaleString()} trades`
                        : "No trades yet"}
                    </div>
                  </div>
                </div>
              </Link>
            );
          })}
        </section>
      )}

      <SortBar sortKey={sortKey} onSort={setSortKey} />
    </div>
  );
}

function SortBar({
  sortKey,
  onSort,
}: {
  sortKey: SortKey;
  onSort: (k: SortKey) => void;
}) {
  const options: { key: SortKey; label: string }[] = [
    { key: "symbol", label: "Symbol" },
    { key: "price", label: "Price" },
    { key: "change", label: "% Change" },
    { key: "volume", label: "Volume" },
    { key: "turnover", label: "Turnover" },
  ];
  return (
    <div className="mt-5 flex flex-wrap items-center gap-2 text-xs text-muted">
      <span className="uppercase tracking-wide">Sort cards by:</span>
      {options.map((o) => (
        <button
          key={o.key}
          onClick={() => onSort(o.key)}
          className={`rounded-full border px-2.5 py-1 transition ${
            sortKey === o.key
              ? "border-accent/40 bg-accent/10 text-accent"
              : "border-panel-border hover:text-white"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
