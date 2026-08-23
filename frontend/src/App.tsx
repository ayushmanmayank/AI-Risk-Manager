import { Route, Routes } from 'react-router-dom';
import { Layout } from './components/Layout';
import { ChargebackCenter } from './pages/ChargebackCenter';
import { ChargebackDetail } from './pages/ChargebackDetail';
import { Dashboard } from './pages/Dashboard';
import { FraudSpike } from './pages/FraudSpike';
import { HighRiskTransactions } from './pages/HighRiskTransactions';
import { ModelPerformance } from './pages/ModelPerformance';
import { ThresholdSimulator } from './pages/ThresholdSimulator';
import { TransactionDetail } from './pages/TransactionDetail';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/high-risk" element={<HighRiskTransactions />} />
        <Route path="/transactions/:id" element={<TransactionDetail />} />
        <Route path="/fraud-spike" element={<FraudSpike />} />
        <Route path="/threshold-simulator" element={<ThresholdSimulator />} />
        <Route path="/model-performance" element={<ModelPerformance />} />
        <Route path="/chargebacks" element={<ChargebackCenter />} />
        <Route path="/chargebacks/:id" element={<ChargebackDetail />} />
        {/* Anything else is a later day; falls through to the catch-all
            below intentionally. */}
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

function NotFound() {
  return (
    <div className="card p-10 text-center">
      <p className="font-display text-lg font-semibold text-text-primary">Page not built yet</p>
      <p className="mt-2 text-sm text-text-secondary">This page is planned for a later day of the sprint.</p>
    </div>
  );
}
