import { NavLink, Outlet } from 'react-router-dom';

const NAV_LINKS = [
  // Deliberately first, above Dashboard -- this is the one nav entry aimed
  // at a judge doing an evaluation pass rather than at demo/workflow use,
  // so it gets the opposite placement decision from Tier 3B's drift
  // monitor (a lower-priority capability that stayed off the nav entirely):
  // here, being found first IS the page's job. See SubmissionMapping.tsx.
  { to: '/submission', label: 'Submission' },
  { to: '/', label: 'Dashboard' },
  { to: '/high-risk', label: 'High-Risk Transactions' },
  { to: '/fraud-spike', label: 'Fraud Spike' },
  { to: '/threshold-simulator', label: 'Threshold Simulator' },
  { to: '/model-performance', label: 'Model Performance' },
  { to: '/chargebacks', label: 'Chargebacks' },
];

/** Left icon-rail-style nav -- text labels, not icons. This app has one
 * vertical rail (brand block + links stacked), not a separate horizontal
 * top bar; the layout-revision brief's "header" and "left nav panel" are
 * treated as this same rail here (there's nothing else to make dark).
 *
 * Off-black rail (--color-surface-inverse -- the same token card-dark
 * uses for Dashboard's cards, so header/nav/cards genuinely share one
 * value, not several similar-looking shades), off-white text, EXCEPT:
 * - the brand block at the very top, which stays the off-white canvas
 *   color as a deliberate, hard-edged exception (a solid border, not a
 *   gradient) -- the one bright anchor point in an otherwise dark rail.
 * - the active nav item's label, which stays off-white (not accent --
 *   see below for why) with a small accent-colored left-border marker
 *   indicating current page.
 *
 * The active-state accent marker is a border/background wash, not the
 * link's TEXT color: the real accent (#c4321e) measures only 3.28:1 on
 * this dark background (fails WCAG AA for normal text, 4.5:1 minimum) --
 * see theme/colors.ts's ACCENT_ON_DARK docstring. A marker only needs to
 * clear the 3:1 non-text threshold, which it does, so this keeps the
 * accent's wayfinding role visible without an under-contrast label.
 */
export function Layout() {
  return (
    <div className="min-h-screen bg-bg-base font-sans text-text-primary">
      <div className="flex min-h-screen">
        <nav className="flex w-56 shrink-0 flex-col border-r border-border-on-dark bg-surface-inverse">
          {/* A full orange BORDER around this block read as too heavy on
              follow-up review and was removed -- back to the plain
              bottom rule matching the rest of the nav's hairlines. The
              accent branding touch moved onto the wordmark's letters
              instead: a faded orange glow (text-shadow, not a hard
              outline) picking up the same accent at low opacity. */}
          <div className="border-b border-border bg-bg-base px-5 py-5">
            <span
              className="font-display text-base font-semibold tracking-tight text-text-primary"
              style={{ textShadow: '0 0 5px color-mix(in srgb, var(--color-accent) 45%, transparent)' }}
            >
              AI Risk Manager
            </span>
          </div>
          <div className="flex-1 space-y-0.5 p-3">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === '/'}
                className={({ isActive }) =>
                  `block border-l-2 px-3 py-2 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-text-primary-on-dark)] focus-visible:outline-offset-2 ${
                    isActive
                      ? 'border-accent bg-accent/10 font-medium text-text-primary-on-dark'
                      : 'border-transparent text-text-secondary-on-dark hover:bg-white/5 hover:text-text-primary-on-dark'
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        </nav>
        <main className="min-w-0 flex-1 overflow-x-auto bg-canvas-grid px-8 py-8">
          {/* Shared, centered content column -- ONE max-width for every
              page, applied here rather than per-page, so no page can end
              up with lopsided leftover whitespace on one side (this
              replaced SubmissionMapping's own ad hoc `max-w-4xl`, which
              wasn't centered and was the specific case flagged). Pages
              with genuinely wide content (the two data tables) still get
              real room -- 1280px comfortably fits their columns while
              still reading as a bounded, centered page on very wide
              viewports. */}
          <div className="mx-auto w-full max-w-7xl">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
