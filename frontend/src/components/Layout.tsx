import { NavLink, Outlet } from 'react-router-dom';

const NAV_LINKS = [
  { to: '/', label: 'Dashboard' },
  { to: '/high-risk', label: 'High-Risk Transactions' },
  { to: '/fraud-spike', label: 'Fraud Spike' },
  { to: '/threshold-simulator', label: 'Threshold Simulator' },
  { to: '/model-performance', label: 'Model Performance' },
  { to: '/chargebacks', label: 'Chargebacks' },
];

export function Layout() {
  return (
    <div className="min-h-screen bg-[#f9f9f7]">
      <header className="border-b border-[#e1e0d9] bg-[#fcfcfb]">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <span className="text-lg font-semibold text-[#0b0b0b]">AI Risk Manager</span>
          <nav className="flex gap-6">
            {NAV_LINKS.map((link) => (
              <NavLink
                key={link.to}
                to={link.to}
                className={({ isActive }) =>
                  `text-sm ${isActive ? 'font-semibold text-[#0b0b0b]' : 'font-medium text-[#898781] hover:text-[#52514e]'}`
                }
              >
                {link.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
