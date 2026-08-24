interface ChangeValueProps {
  /** Percentage change, e.g. 1.24 or -0.87 */
  pct?: number | null;
  /** Show arrow icon */
  arrow?: boolean;
  className?: string;
}

/** Colored +/− percentage indicator used across tables and cards. */
export default function ChangeBadge({
  pct,
  arrow = true,
  className = "",
}: ChangeValueProps) {
  if (pct === null || pct === undefined || Number.isNaN(pct)) {
    return <span className={`text-muted ${className}`}>—</span>;
  }

  const positive = pct >= 0;
  const colorClass = positive ? "text-positive" : "text-negative";

  return (
    <span
      className={`inline-flex items-center gap-1 font-medium tabular-nums ${colorClass} ${className}`}
    >
      {arrow && (
        <svg
          viewBox="0 0 12 12"
          className={`h-2.5 w-2.5 ${positive ? "" : "rotate-180"}`}
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M6 1.5l4.5 6h-9z" />
        </svg>
      )}
      {positive ? "+" : ""}
      {pct.toFixed(2)}%
    </span>
  );
}
