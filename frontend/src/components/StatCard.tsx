import type { ReactNode } from "react";

interface StatCardProps {
  label: string;
  value: ReactNode;
  sublabel?: ReactNode;
  tone?: "positive" | "negative";
}

export default function StatCard({ label, value, sublabel, tone }: StatCardProps) {
  const toneClass =
    tone === "positive" ? "text-positive" : tone === "negative" ? "text-negative" : "";

  return (
    <div className="rounded-xl border border-panel-border bg-panel px-4.5 py-4">
      <div className="mb-1.5 text-xs text-muted">{label}</div>
      <div className={`text-xl font-semibold ${toneClass}`}>{value}</div>
      {sublabel && <div className="mt-1 text-xs text-muted">{sublabel}</div>}
    </div>
  );
}
