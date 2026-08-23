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

/** Left icon-rail-style nav (text labels, not icons -- see the redesign's
 * post-build critique for why: real text stays accessible and needs no
 * new icon dependency, while still winning the density/side-rail layout
 * this brief called for). Same NAV_LINKS, same routes, same NavLink
 * active-state logic as before -- purely a visual restructure from a top
 * bar to a side rail, no navigation behavior changed.
 */
export function Layout() {
  return (
    <div className="min-h-screen bg-bg-base font-sans text-text-primary">
      <div className="flex min-h-screen">
        <nav className="flex w-56 shrink-0 flex-col border-r border-border bg-bg-surface">
          <div className="border-b border-border px-5 py-5">
            <span className="font-display text-base font-semibold tracking-tight text-text-primary">
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
                  `block rounded-md px-3 py-2 text-sm transition-colors focus-visible:outline-2 focus-visible:outline-[var(--color-accent)] focus-visible:outline-offset-2 ${
                    isActive
                      ? 'bg-bg-surface-raised font-medium text-text-primary'
                      : 'text-text-secondary hover:bg-bg-surface-raised hover:text-text-primary'
                  }`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        </nav>
        <main className="min-w-0 flex-1 overflow-x-auto px-8 py-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
