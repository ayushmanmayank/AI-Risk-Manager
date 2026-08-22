export function LoadingBlock() {
  return (
    <div className="animate-pulse space-y-4">
      <div className="h-24 rounded-lg border border-[#e1e0d9] bg-[#f0efec]" />
      <div className="h-72 rounded-lg border border-[#e1e0d9] bg-[#f0efec]" />
    </div>
  );
}

export function ErrorBlock({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-[#d03b3b] bg-[#fcfcfb] p-6">
      <p className="font-semibold text-[#d03b3b]">Couldn't load this page</p>
      <p className="mt-1 text-sm text-[#52514e]">{message}</p>
      <button
        onClick={onRetry}
        className="mt-4 rounded-md border border-[#e1e0d9] px-4 py-2 text-sm font-medium text-[#0b0b0b] hover:bg-[#f0efec]"
      >
        Retry
      </button>
    </div>
  );
}

export function EmptyBlock({ title, description }: { title: string; description: string }) {
  return (
    <div className="rounded-lg border border-[#e1e0d9] bg-[#fcfcfb] p-10 text-center">
      <p className="text-lg font-semibold text-[#0b0b0b]">{title}</p>
      <p className="mt-2 text-sm text-[#52514e]">{description}</p>
    </div>
  );
}
