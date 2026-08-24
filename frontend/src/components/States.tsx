interface LoadingProps {
  label?: string;
  className?: string;
}

export function Spinner({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <span
      className={`inline-block animate-spin rounded-full border-2 border-current border-t-transparent ${className}`}
      aria-hidden="true"
    />
  );
}

export function LoadingState({ label = "Loading…", className = "" }: LoadingProps) {
  return (
    <div
      className={`flex min-h-[320px] flex-col items-center justify-center gap-3 text-muted ${className}`}
      role="status"
    >
      <Spinner className="h-8 w-8 text-accent" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function InlineLoading({ label = "Loading…" }: LoadingProps) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-muted" role="status">
      <Spinner className="text-accent" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
}: ErrorStateProps) {
  return (
    <div
      className="rounded-xl border border-negative/25 bg-negative/10 px-5 py-4"
      role="alert"
    >
      <h3 className="font-semibold text-negative">{title}</h3>
      <p className="mt-1 text-sm text-negative/90">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 rounded-lg border border-negative/30 bg-negative/20 px-3.5 py-1.5 text-xs font-medium text-white transition hover:bg-negative/30"
        >
          Retry
        </button>
      )}
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  hint?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, hint, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-[180px] flex-col items-center justify-center gap-1.5 rounded-xl border border-dashed border-panel-border px-6 py-10 text-center">
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        className="mb-2 h-8 w-8 text-muted opacity-60"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
        />
      </svg>
      <p className="text-sm font-medium">{title}</p>
      {hint && <p className="max-w-md text-xs text-muted">{hint}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
