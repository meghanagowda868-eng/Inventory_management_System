import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { inventoryApi } from '../api/inventoryApi';
import { aiApi } from '../api/aiApi';
import { StatCard } from '../components/ui/StatCard';
import StockBadge from '../components/inventory/StockBadge';
import { useAuth } from '../context/AuthContext';
import {
  Chart as ChartJS,
  ArcElement, Tooltip, Legend,
  CategoryScale, LinearScale, BarElement, Title,
} from 'chart.js';
import { Doughnut, Bar } from 'react-chartjs-2';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title);

const CHART_OPTIONS = {
  responsive: true,
  plugins: {
    legend: { labels: { color: '#94a3b8', font: { family: 'Inter' } } },
  },
  scales: {
    x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
    y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
  },
};

export default function Dashboard() {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';
  const isManager = user?.role === 'manager';

  const { data: productsData } = useQuery({
    queryKey: ['products', { page_size: 100 }],
    queryFn: () => inventoryApi.listProducts({ page_size: 100 }).then(r => r.data),
    staleTime: 30000,
  });

  const { data: insights } = useQuery({
    queryKey: ['ai-insights'],
    queryFn: () => aiApi.getInsights().then(r => r.data),
    staleTime: 60000,
  });

  const { data: lowStock } = useQuery({
    queryKey: ['low-stock'],
    queryFn: () => inventoryApi.getLowStock().then(r => r.data),
    staleTime: 30000,
  });

  const { data: dashboardSummary } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: () => inventoryApi.getDashboardSummary().then(r => r.data),
    staleTime: 30000,
  });

  const { data: reorderSummary } = useQuery({
    queryKey: ['reorders-summary'],
    queryFn: () => inventoryApi.getReorderSummary().then(r => r.data),
    staleTime: 30000,
  });

  const { data: requiredReorders = [] } = useQuery({
    queryKey: ['reorders-required'],
    queryFn: () => inventoryApi.getRequiredReorders().then(r => r.data),
    staleTime: 30000,
  });

  const { data: recentMovements } = useQuery({
    queryKey: ['recent-movements'],
    queryFn: () => inventoryApi.getRecentMovements(5).then(r => r.data),
    staleTime: 30000,
  });

  const { data: riskSnapshot } = useQuery({
    queryKey: ['risk-snapshot'],
    queryFn: () => inventoryApi.getRiskSnapshot().then(r => r.data),
    staleTime: 30000,
  });

  const { data: seasonalDemand } = useQuery({
    queryKey: ['seasonal-demand'],
    queryFn: () => inventoryApi.getSeasonalDemand().then(r => r.data),
    enabled: isAdmin || isManager,
    staleTime: 60000,
  });

  const { data: offers = [] } = useQuery({
    queryKey: ['offers'],
    queryFn: () => inventoryApi.listOffers().then(r => r.data),
    staleTime: 60000,
  });

  const products = productsData?.items ?? [];
  const totalProducts = dashboardSummary?.total_products ?? productsData?.total ?? 0;
  const lowStockCount = dashboardSummary?.low_stock_products ?? lowStock?.length ?? 0;
  const outOfStockCount = dashboardSummary?.out_of_stock_products ?? products.filter(p => p.stock_status === 'out_of_stock').length;
  const inventoryHealth = dashboardSummary?.inventory_health_score ?? 100;
  const totalValue = products.reduce((sum, p) => sum + (p.price * p.quantity), 0);
  const healthyStockCount = Math.max(0, totalProducts - lowStockCount - outOfStockCount);

  const catMap = {};
  products.forEach(p => {
    const cat = p.category || 'Uncategorized';
    catMap[cat] = (catMap[cat] || 0) + p.quantity;
  });
  const catLabels = Object.keys(catMap).slice(0, 8);
  const catValues = catLabels.map(k => catMap[k]);

  const barData = {
    labels: catLabels,
    datasets: [{
      label: 'Stock Quantity',
      data: catValues,
      backgroundColor: 'rgba(99,102,241,0.7)',
      borderColor: '#6366f1',
      borderWidth: 1,
      borderRadius: 6,
    }],
  };

  const doughnutData = {
    labels: ['Available', 'Low Stock', 'Out of Stock'],
    datasets: [{
      data: [healthyStockCount, lowStockCount, outOfStockCount],
      backgroundColor: ['rgba(16,185,129,0.8)', 'rgba(245,158,11,0.8)', 'rgba(239,68,68,0.8)'],
      borderColor: ['#10b981', '#f59e0b', '#ef4444'],
      borderWidth: 2,
    }],
  };

  const kpis = [
    { to: '/inventory', icon: '▣', label: 'Total Products', value: totalProducts.toLocaleString(), iconBg: 'rgba(99,102,241,0.15)', trend: 12, trendLabel: 'vs last month' },
    { to: '/inventory', icon: '₿', label: 'Inventory Value', value: `$${totalValue.toLocaleString('en-US', { minimumFractionDigits: 0 })}`, iconBg: 'rgba(16,185,129,0.15)', trend: 8, trendLabel: 'growth' },
    { to: '/inventory?stock_status=low_stock', icon: '⚠', label: 'Low Stock', value: lowStockCount, iconBg: 'rgba(245,158,11,0.15)', trend: -3, trendLabel: 'needs attention' },
    { to: '/inventory?stock_status=out_of_stock', icon: '⛔', label: 'Out of Stock', value: outOfStockCount, iconBg: 'rgba(239,68,68,0.15)', trend: 2, trendLabel: 'recent' },
  ];

  const movementRows = recentMovements ?? [];
  const riskItems = riskSnapshot?.items ?? [];

  return (
    <div className="page-content fade-in dashboard-shell">
      <section className="hero-panel card">
        <div className="hero-content">
          <div>
            <span className="eyebrow">Inventory Command Center</span>
            <h1 className="page-title hero-title">{isAdmin ? 'Admin control, optimized.' : isManager ? 'Operations pulse, in focus.' : 'Welcome back.'}</h1>
            <p className="page-subtitle hero-subtitle">
              {isAdmin
                ? 'Track product lifecycle, replenishment workflows, and supply risk in one premium command view.'
                : isManager
                  ? 'Monitor stock movement, replenishment requests, and purchase orders.'
                  : 'Your inventory performance overview is ready.'}
            </p>
          </div>
          <div className="hero-actions">
            <Link to="/sales" className="btn btn-primary shadow-lg shadow-indigo-500/25">
              🛒 New Sale / POS
            </Link>
            <Link to="/reorders" className="btn btn-secondary">
              ⚡ Reorder Center
            </Link>
            <Link to="/reports" className="btn btn-secondary">
              📊 Valuation & Reports
            </Link>
          </div>
        </div>
      </section>

      {/* ── QUICK ACTION LAUNCHPAD ───────────────────────────────────────── */}
      <div className="card p-3.5 mb-6 bg-slate-900/60 border border-slate-700/60 rounded-2xl flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-300">
          <span className="text-base text-indigo-400">⚡</span> Quick Operations:
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to="/sales"
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition flex items-center gap-1.5"
          >
            <span>🛒</span> New Sale Checkout
          </Link>
          <Link
            to="/purchase-orders"
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-indigo-500/10 hover:bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 transition flex items-center gap-1.5"
          >
            <span>📦</span> Issue Purchase Order
          </Link>
          <Link
            to="/reorders"
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition flex items-center gap-1.5"
          >
            <span>⚡</span> Review Reorders ({reorderSummary?.products_requiring_reorder ?? 0})
          </Link>
          <Link
            to="/ai-insights"
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-purple-500/10 hover:bg-purple-500/20 text-purple-300 border border-purple-500/30 transition flex items-center gap-1.5"
          >
            <span>✦</span> AI Demand Forecast
          </Link>
        </div>
      </div>

      <div className="stats-grid premium-stats">
        {kpis.map((card) => (
          <Link key={card.label} to={card.to} className="stat-card-link">
            <StatCard
              icon={card.icon}
              label={card.label}
              value={card.value}
              iconBg={card.iconBg}
              trend={card.trend}
              trendLabel={card.trendLabel}
            />
          </Link>
        ))}
      </div>

      {/* ── REORDER & PROCUREMENT WORKFLOW OVERVIEW ────────────────────────── */}
      <div className="card p-6" style={{ marginBottom: 24 }}>
        <div className="section-header-row flex-between" style={{ marginBottom: 16 }}>
          <div>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0 }}>⚡ Reorder & Procurement Pipeline</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '4px 0 0' }}>
              Real-time threshold detection and purchase order replenishment status.
            </p>
          </div>
          <Link to="/reorders" className="btn btn-primary btn-sm">
            Open Reorder System →
          </Link>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 14 }}>
          <Link to="/reorders" style={{ textDecoration: 'none' }}>
            <div style={{ background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.25)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Products to Reorder</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#ff5d7a', marginTop: 4 }}>
                {reorderSummary?.products_requiring_reorder ?? requiredReorders.length}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Stock ≤ Reorder Point</div>
            </div>
          </Link>

          <Link to="/reorders" style={{ textDecoration: 'none' }}>
            <div style={{ background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.25)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Pending Requests</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#f7b955', marginTop: 4 }}>
                {reorderSummary?.pending_requests ?? 0}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Awaiting manager review</div>
            </div>
          </Link>

          <Link to="/reorders" style={{ textDecoration: 'none' }}>
            <div style={{ background: 'rgba(91,124,255,0.12)', border: '1px solid rgba(91,124,255,0.25)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Approved Requests</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#5b7cff', marginTop: 4 }}>
                {reorderSummary?.approved_requests ?? 0}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Ready for PO issue</div>
            </div>
          </Link>

          <Link to="/purchase-orders" style={{ textDecoration: 'none' }}>
            <div style={{ background: 'rgba(139,92,246,0.12)', border: '1px solid rgba(139,92,246,0.25)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Orders in Transit</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#8b5cf6', marginTop: 4 }}>
                {reorderSummary?.orders_in_transit ?? 0}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Active vendor orders</div>
            </div>
          </Link>

          <Link to="/purchase-orders" style={{ textDecoration: 'none' }}>
            <div style={{ background: 'rgba(99,212,255,0.12)', border: '1px solid rgba(99,212,255,0.25)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Partially Received</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#63d4ff', marginTop: 4 }}>
                {reorderSummary?.partially_received_orders ?? 0}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Inbound deliveries</div>
            </div>
          </Link>

          <Link to="/purchase-orders" style={{ textDecoration: 'none' }}>
            <div style={{ background: 'rgba(30,201,139,0.12)', border: '1px solid rgba(30,201,139,0.25)', borderRadius: 'var(--radius-md)', padding: '14px 16px' }}>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-soft)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Recently Received</div>
              <div style={{ fontSize: '1.6rem', fontWeight: 700, color: '#1ec98b', marginTop: 4 }}>
                {reorderSummary?.recently_received_stock ?? 0}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>Completed receipts</div>
            </div>
          </Link>
        </div>
      </div>

      <div className="dashboard-lower-grid">
        {(isAdmin || isManager) && <Link to="/seasonal-demand" className="card dashboard-summary-link">
          <div className="section-header-row"><h2>Seasonal Demand</h2><span className="pill info">Planning</span></div>
          <div className="insight-list"><div className="insight-item"><strong>{seasonalDemand?.season || 'No event'}</strong><span>{seasonalDemand?.days_remaining ?? 0} days remaining</span></div><div className="insight-item"><strong>{seasonalDemand?.recommendations?.filter(item => item.demand_level === 'HIGH').length ?? 0}</strong><span>High-demand products</span></div></div>
        </Link>}
        <Link to="/offers" className="card dashboard-summary-link">
          <div className="section-header-row"><h2>Festive Offers</h2><span className="pill success">Live</span></div>
          <div className="insight-list"><div className="insight-item"><strong>{offers.filter(offer => offer.status === 'active').length}</strong><span>Active offers</span></div><div className="insight-item"><strong>{offers.filter(offer => offer.status === 'scheduled').length}</strong><span>Scheduled offers</span></div></div>
        </Link>
      </div>

      <div className="charts-grid">
        <div className="card p-6 chart-card">
          <div className="section-header-row">
            <h2>Stock by category</h2>
            <span className="pill neutral">Live</span>
          </div>
          {catLabels.length > 0 ? (
            <Bar data={barData} options={{ ...CHART_OPTIONS, indexAxis: 'x' }} height={220} />
          ) : (
            <div className="empty-state minimal">
              <p>No inventory data available</p>
            </div>
          )}
        </div>

        <div className="card p-6 chart-card">
          <div className="section-header-row">
            <h2>Stock distribution</h2>
            <span className="pill success">Updated</span>
          </div>
          <div className="doughnut-wrap">
            <Doughnut
              data={doughnutData}
              options={{
                responsive: true,
                plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } },
                cutout: '65%',
              }}
            />
          </div>
        </div>
      </div>

      <div className="dashboard-lower-grid">
        <div className="card table-card">
          <div className="section-header-row table-header">
            <h2>Low stock alerts</h2>
            <Link to="/reorders" className="text-link">Reorder center</Link>
          </div>
          {lowStock && lowStock.length > 0 ? (
            <div className="table-wrapper compact-table">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Qty</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {lowStock.slice(0, 5).map((p) => (
                    <tr key={p.id}>
                      <td>
                        <Link to={`/inventory/${p.id}`} className="link-strong">{p.name}</Link>
                      </td>
                      <td className="qty-cell">{p.quantity}</td>
                      <td><StockBadge status={p.stock_status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="empty-state">
              <p>All products are comfortably stocked.</p>
            </div>
          )}
        </div>

        <div className="card insight-card">
          <div className="section-header-row table-header">
            <h2>AI intelligence</h2>
            <span className="pill info">AI</span>
          </div>
          <div className="insight-list">
            {insights ? (
              <>
                <div className="insight-item">
                  <strong>{insights.low_stock_count || 0}</strong>
                  <span>Low-stock alerts</span>
                </div>
                <div className="insight-item">
                  <strong>{insights.out_of_stock_count || 0}</strong>
                  <span>Out-of-stock items</span>
                </div>
                <div className="insight-item">
                  <strong>{inventoryHealth}/100</strong>
                  <span>Inventory health</span>
                </div>
              </>
            ) : (
              <div className="empty-state minimal">
                <p>AI summary is unavailable</p>
              </div>
            )}
          </div>

          <div className="section-header-row table-header" style={{ marginTop: '18px' }}>
            <h2>Recent movements</h2>
          </div>
          {movementRows.length > 0 ? (
            <div className="insight-list">
              {movementRows.map((movement) => (
                <div key={movement.id} className="insight-item">
                  <div>
                    <strong>{movement.product_name}</strong>
                    <div style={{ color: '#8fa0bc', fontSize: '0.72rem' }}>{movement.movement_type} · {movement.warehouse_name}</div>
                  </div>
                  <span>{movement.quantity}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state minimal">
              <p>No recent movements</p>
            </div>
          )}

          <div className="section-header-row table-header" style={{ marginTop: '18px' }}>
            <h2>Risk watchlist</h2>
          </div>
          {riskItems.length > 0 ? (
            <div className="insight-list">
              {riskItems.map((item) => (
                <div key={item.product_id} className="insight-item">
                  <div>
                    <strong>{item.product_name}</strong>
                    <div style={{ color: '#8fa0bc', fontSize: '0.72rem' }}>{item.sku} · qty {item.quantity}</div>
                  </div>
                  <span style={{ fontWeight: 700, color: item.risk_level === 'critical' ? '#ff7a9c' : item.risk_level === 'high' ? '#f7b955' : '#8cc8ff' }}>
                    {item.risk_score}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state minimal">
              <p>No active risk items</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
