export function LoadingBlock() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-24 rounded-2xl border border-border bg-bg-surface-raised" />
      <div className="h-72 rounded-2xl border border-border bg-bg-surface-raised" />
    </div>
  );
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-2xl border border-risk-high bg-bg-surface p-6">
      <p className="font-display font-semibold text-risk-high">Couldn't load this page</p>
      <p className="mt-1 text-sm text-text-secondary">{message}</p>
      <button
        onClick={onRetry}
        className="mt-4 rounded-md border border-border px-4 py-2 text-sm font-medium text-text-primary hover:bg-bg-surface-raised focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] focus-visible:outline-offset-2"
      >
        Retry
      </button>
    </div>
  );
}

export function EmptyBlock({ title, description }: { title: string; description: string }) {
  return (
    <div className="card p-10 text-center">
      <p className="font-display text-lg font-semibold text-text-primary">{title}</p>
      <p className="mt-2 text-sm text-text-secondary">{description}</p>
    </div>
  );
}
