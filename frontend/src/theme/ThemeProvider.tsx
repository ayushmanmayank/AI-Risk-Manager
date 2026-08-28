import { createContext, useCallback, useContext, useLayoutEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { ThemeMode } from './colors';

const STORAGE_KEY = 'ai-risk-manager-theme';

interface ThemeContextValue {
  mode: ThemeMode;
  toggle: () => void;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

function readStoredMode(): ThemeMode | null {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    return stored === 'light' || stored === 'dark' ? stored : null;
  } catch {
    // Private browsing / storage disabled -- fall through to the default.
    return null;
  }
}

/**
 * Real deployed app (not a claude.ai Artifact), so persisting the user's
 * theme choice in localStorage is the standard, appropriate approach here
 * -- same discipline as any other production web app's theme toggle.
 * Dark is the default whenever nothing is stored yet, per the spec; once
 * a person flips the toggle, that choice sticks across reloads/sessions
 * on this browser.
 *
 * Sets `data-theme` on <html> (not just a class) so index.css's
 * `:root[data-theme="dark"]` / `[data-theme="light"]` selectors -- and
 * Tailwind's color utilities, which resolve through those custom
 * properties -- pick it up with no other wiring needed anywhere else in
 * the app.
 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(() => readStoredMode() ?? 'dark');

  // useLayoutEffect (not useEffect): runs synchronously before the
  // browser paints, so a person who previously chose light mode doesn't
  // see a flash of the dark default first. index.html also sets the
  // attribute inline before React even loads, for the same reason on the
  // very first paint -- this is a belt-and-suspenders second pass for
  // subsequent re-renders / StrictMode's double-invoke.
  useLayoutEffect(() => {
    document.documentElement.setAttribute('data-theme', mode);
    try {
      window.localStorage.setItem(STORAGE_KEY, mode);
    } catch {
      // Storage unavailable -- the toggle still works for this session,
      // it just won't persist across reloads. Not worth surfacing as an
      // error to the user over a cosmetic preference.
    }
  }, [mode]);

  const toggle = useCallback(() => {
    setMode((previous) => (previous === 'dark' ? 'light' : 'dark'));
  }, []);

  const value = useMemo(() => ({ mode, toggle }), [mode, toggle]);

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

/** Convenience for call sites that only need the mode (chart color
 * resolution), not the toggle function. */
export function useThemeMode(): ThemeMode {
  return useTheme().mode;
}
