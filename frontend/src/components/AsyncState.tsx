import { Skeleton } from './ui/skeleton';

export function LoadingBlock() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-24" />
      <Skeleton className="h-72" />
    </div>
  );
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="card border-accent-rose/50 p-6">
      <p className="font-display font-semibold text-accent-rose">Couldn't load this page</p>
      <p className="mt-1 text-sm text-text-secondary">{message}</p>
      <button
        onClick={onRetry}
        className="pill-glow mt-4 rounded-full border border-border px-4 py-2 text-sm font-medium text-text-primary transition-colors duration-150 hover:bg-bg-surface-raised active:bg-bg-surface-raised focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2"
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
