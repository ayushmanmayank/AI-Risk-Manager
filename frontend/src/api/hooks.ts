import { useCallback, useEffect, useRef, useState } from 'react';

export type AsyncState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: T };

/**
 * Fetch-on-mount (+ refetch) helper shared by every page that pulls from the
 * API. Keeps loading / error / success explicit so no page can accidentally
 * render a blank screen while data is in flight or the backend is down.
 *
 * `deps` lets a page refetch when its own inputs change (e.g. TransactionDetail
 * passing [id]) without remounting -- React Router keeps a page mounted when
 * only the dynamic route segment changes, so without this a page would keep
 * showing stale data for the previous id.
 */
export function useApiData<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
): AsyncState<T> & { refetch: () => void } {
  const [state, setState] = useState<AsyncState<T>>({ status: 'loading' });
  const [reloadKey, setReloadKey] = useState(0);

  const refetch = useCallback(() => setReloadKey((key) => key + 1), []);

  useEffect(() => {
    let cancelled = false;
    setState({ status: 'loading' });

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: 'success', data });
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({ status: 'error', error: error instanceof Error ? error : new Error(String(error)) });
        }
      });

    return () => {
      cancelled = true;
    };
    // fetcher is intentionally excluded: callers pass a fresh closure each
    // render, and re-running only on reloadKey/deps is what makes refetch()
    // work without an infinite fetch loop.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadKey, ...deps]);

  return { ...state, refetch };
}

export type PollingState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: Error }
  | { status: 'success'; data: T; isStale: boolean; lastPollError: Error | null };

/**
 * Like useApiData, but re-fetches on a fixed interval instead of only on
 * mount/refetch() -- used by pages that need to reflect live backend state
 * (the Fraud Spike page polling GET /api/v1/alerts). Deliberately does NOT
 * flash back to the loading skeleton on every poll tick: once there's good
 * data, it stays on screen while a poll is in flight, and a poll failure
 * only sets `isStale` rather than replacing the page with an error screen
 * -- a single transient network blip shouldn't blank out an otherwise-live
 * dashboard. The first fetch still uses the normal loading/error states,
 * so a genuinely-down backend is still reported clearly on initial load.
 */
export function usePolling<T>(fetcher: () => Promise<T>, intervalMs: number): PollingState<T> & { refetch: () => void } {
  const [state, setState] = useState<PollingState<T>>({ status: 'loading' });
  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  const poll = useCallback(() => {
    fetcherRef.current()
      .then((data) => {
        setState({ status: 'success', data, isStale: false, lastPollError: null });
      })
      .catch((error: unknown) => {
        const err = error instanceof Error ? error : new Error(String(error));
        setState((previous) =>
          previous.status === 'success' ? { ...previous, isStale: true, lastPollError: err } : { status: 'error', error: err },
        );
      });
    // fetcherRef defers to the latest closure without retriggering the
    // effect below, same rationale as useApiData's fetcher exclusion.
  }, []);

  useEffect(() => {
    poll();
    const id = window.setInterval(poll, intervalMs);
    return () => window.clearInterval(id);
  }, [poll, intervalMs]);

  return { ...state, refetch: poll };
}

/**
 * Like useApiData, but re-fetches whenever `deps` change instead of only
 * on mount/refetch(), and does NOT flash back to the loading skeleton on
 * those changes -- used by the Threshold Simulator's slider, where every
 * debounced threshold change should update the numbers smoothly rather
 * than blanking the page each time. The first fetch still uses the normal
 * loading/error states. A transient error on a later fetch (deps already
 * changed once successfully) is swallowed silently rather than replacing
 * good data with an error screen -- the next debounced change will retry
 * anyway.
 */
export function useLiveApiData<T>(fetcher: () => Promise<T>, deps: unknown[] = []): AsyncState<T> {
  const [state, setState] = useState<AsyncState<T>>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;

    fetcher()
      .then((data) => {
        if (!cancelled) setState({ status: 'success', data });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState((previous) => {
          if (previous.status === 'success') return previous;
          return { status: 'error', error: error instanceof Error ? error : new Error(String(error)) };
        });
      });

    return () => {
      cancelled = true;
    };
    // fetcher intentionally excluded, same rationale as useApiData.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return state;
}
