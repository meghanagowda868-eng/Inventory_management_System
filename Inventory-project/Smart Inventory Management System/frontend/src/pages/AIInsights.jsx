import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { aiApi } from '../api/aiApi';
import { inventoryApi } from '../api/inventoryApi';

export default function AIInsights() {
  const [nlQuery, setNlQuery] = useState('');
  const [nlResult, setNlResult] = useState(null);
  const [nlLoading, setNlLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState([
    {
      role: 'assistant',
      text: 'Hi! I can help you view, create, update, and delete products. Try: “Create a new product called Laptop Pro 15 with SKU LAPTOP-PRO-15 and price 1299”.',
    },
  ]);
  const [reorderData, setReorderData] = useState({ product_id: '', current_stock: '', minimum_stock: '', average_daily_sales: '' });
  const [reorderResult, setReorderResult] = useState(null);
  const [reorderError, setReorderError] = useState('');
  const [reorderLoading, setReorderLoading] = useState(false);

  const { data: insights, isLoading: insightsLoading } = useQuery({
    queryKey: ['ai-insights'],
    queryFn: () => aiApi.getInsights().then(r => r.data),
    staleTime: 60000,
  });

  const { data: lowStockProducts } = useQuery({
    queryKey: ['low-stock'],
    queryFn: () => inventoryApi.getLowStock().then(r => r.data),
    staleTime: 30000,
  });

  const { data: products = [] } = useQuery({
    queryKey: ['reorder-products'],
    queryFn: async () => {
      const [firstPage, secondPage] = await Promise.all([
        inventoryApi.listProducts({ page: 1, page_size: 100 }),
        inventoryApi.listProducts({ page: 2, page_size: 100 }),
      ]);
      return [...firstPage.data.items, ...secondPage.data.items];
    },
    staleTime: 30000,
  });

  const handleNlQuery = async (e) => {
    e.preventDefault();
    const trimmed = nlQuery.trim();
    if (!trimmed) return;

    setNlLoading(true);
    const userMessage = { role: 'user', text: trimmed };
    setChatMessages(prev => [...prev, userMessage]);

    try {
      const { data } = await aiApi.nlQuery(trimmed);
      setNlResult(data);
      setChatMessages(prev => [...prev, { role: 'assistant', text: data.answer }]);
    } catch {
      const fallback = { answer: 'Query failed. Please try again.', suggestions: [] };
      setNlResult(fallback);
      setChatMessages(prev => [...prev, { role: 'assistant', text: fallback.answer }]);
    } finally {
      setNlLoading(false);
      setNlQuery('');
    }
  };

  const handleReorder = async (e) => {
    e.preventDefault();
    setReorderError('');
    setReorderLoading(true);
    try {
      const { data } = await aiApi.reorderSuggestion({
        product_id: parseInt(reorderData.product_id),
        product_name: products.find(product => product.id === parseInt(reorderData.product_id))?.name || 'Selected Product',
        current_stock: parseInt(reorderData.current_stock),
        minimum_stock: parseInt(reorderData.minimum_stock),
        average_daily_sales: parseFloat(reorderData.average_daily_sales),
        lead_time_days: 7,
      });
      setReorderResult(data);
    } catch (error) {
      setReorderResult(null);
      setReorderError(
        error.response?.data?.detail
          || 'Unable to calculate a suggestion. Check the API connection and try again.',
      );
    } finally {
      setReorderLoading(false);
    }
  };

  const urgencyConfig = {
    critical: { cls: 'badge-danger', label: '🚨 Critical' },
    high: { cls: 'badge-warning', label: '⚠️ High' },
    medium: { cls: 'badge-info', label: '📋 Medium' },
    low: { cls: 'badge-success', label: '✅ Low' },
  };

  const SAMPLE_QUERIES = [
    'Show me all low stock products',
    'What is the total inventory value?',
    'How many products are out of stock?',
    'Which category has the highest stock?',
  ];

  return (
    <div className="page-content fade-in">
      <div className="page-header">
        <h1 className="page-title">🤖 AI Insights</h1>
        <p className="page-subtitle">Powered by scikit-learn — demand prediction, reorder suggestions, and natural language queries</p>
      </div>

      {/* Inventory Overview Insights */}
      <div className="card p-6" style={{ marginBottom: 24 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>📊 Inventory Overview</h2>
        {insightsLoading ? (
          <div className="flex-center" style={{ height: 80 }}><div className="spinner" /></div>
        ) : insights ? (
          <div className="stats-grid" style={{ marginBottom: 0 }}>
            {[
              { label: 'Total Products', value: insights.total_products, icon: '📦', bg: 'rgba(99,102,241,0.15)' },
              { label: 'Inventory Value', value: `$${Number(insights.total_inventory_value).toLocaleString()}`, icon: '💰', bg: 'rgba(16,185,129,0.15)' },
              { label: 'Low Stock', value: insights.low_stock_count, icon: '⚠', bg: 'rgba(245,158,11,0.15)' },
              { label: 'Out of Stock', value: insights.out_of_stock_count, icon: '🚫', bg: 'rgba(239,68,68,0.15)' },
              { label: 'Healthy Stock', value: insights.healthy_stock_count, icon: '✅', bg: 'rgba(16,185,129,0.15)' },
              { label: 'Low Stock %', value: `${insights.low_stock_percentage}%`, icon: '📉', bg: 'rgba(99,102,241,0.1)' },
            ].map(({ label, value, icon, bg }) => (
              <div key={label} className="stat-card">
                <div className="stat-icon" style={{ background: bg }}>{icon}</div>
                <div>
                  <div className="stat-value" style={{ fontSize: 22 }}>{value}</div>
                  <div className="stat-label">{label}</div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--color-text-muted)' }}>Unable to fetch insights. Make sure inventory service is running.</p>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24 }}>
        {/* Natural Language Query */}
        <div className="card p-6">
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>💬 Natural Language Query</h2>
          <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 16 }}>
            Ask questions about your inventory in plain English.
          </p>

          <form onSubmit={handleNlQuery} style={{ marginBottom: 16 }}>
            <div className="form-group">
              <input
                id="nl-query-input"
                type="text"
                className="form-input"
                placeholder="e.g. Show me all low stock products"
                value={nlQuery}
                onChange={e => setNlQuery(e.target.value)}
              />
            </div>
            <button
              id="nl-query-submit"
              type="submit"
              className="btn btn-primary w-full"
              style={{ justifyContent: 'center' }}
              disabled={nlLoading || !nlQuery.trim()}
            >
              {nlLoading ? <><span className="spinner" style={{ width: 16, height: 16, borderWidth: 2 }} /> Querying...</> : '🔍 Ask AI'}
            </button>
          </form>

          {/* Sample queries */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--color-text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Try these</div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {SAMPLE_QUERIES.map(q => (
                <button
                  key={q}
                  onClick={() => setNlQuery(q)}
                  className="btn btn-secondary btn-sm"
                  style={{ fontSize: 11 }}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>

          {/* Result */}
          <div style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 'var(--radius-md)', padding: 12, marginBottom: 16, maxHeight: 420, minHeight: 180, overflowY: 'auto' }}>
            {chatMessages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                style={{
                  display: 'flex',
                  justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                  marginBottom: 8,
                }}
              >
                <div
                  style={{
                    maxWidth: '82%',
                    padding: '10px 12px',
                    borderRadius: 12,
                    background: message.role === 'user' ? 'rgba(99,102,241,0.18)' : 'rgba(15, 23, 42, 0.5)',
                    border: '1px solid rgba(99,102,241,0.2)',
                    color: 'var(--color-text-primary)',
                    fontSize: 13,
                    lineHeight: 1.5,
                  }}
                >
                  {message.text}
                </div>
              </div>
            ))}
          </div>

          {nlResult && (
            <div style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <div style={{ fontSize: 11, color: 'var(--color-accent-light)', fontWeight: 700, marginBottom: 8, textTransform: 'uppercase' }}>
                {nlResult.interpreted_intent}
              </div>
              <p style={{ fontSize: 14, lineHeight: 1.7, marginBottom: 12 }}>{nlResult.answer}</p>
              {nlResult.suggestions?.length > 0 && (
                <div>
                  <div style={{ fontSize: 11, color: 'var(--color-text-muted)', marginBottom: 6 }}>Follow-up suggestions:</div>
                  {nlResult.suggestions.map(s => (
                    <button
                      key={s}
                      onClick={() => setNlQuery(s)}
                      style={{ display: 'block', fontSize: 12, color: 'var(--color-accent-light)', background: 'none', border: 'none', cursor: 'pointer', textAlign: 'left', marginBottom: 4 }}
                    >
                      → {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Reorder Suggestion */}
        <div className="card p-6">
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 8 }}>📋 Smart Reorder Suggestion</h2>
          <p style={{ fontSize: 13, color: 'var(--color-text-muted)', marginBottom: 16 }}>
            Calculate the optimal reorder quantity for any product.
          </p>

          <form onSubmit={handleReorder}>
            <div className="form-group">
              <label className="form-label" htmlFor="reorder-product">Product</label>
              <select
                id="reorder-product"
                className="form-input"
                value={reorderData.product_id}
                onChange={e => {
                  const product = products.find(item => item.id === Number(e.target.value));
                  setReorderData(data => ({
                    ...data,
                    product_id: e.target.value,
                    current_stock: product?.quantity ?? '',
                    minimum_stock: product?.minimum_stock ?? '',
                  }));
                }}
                required
              >
                <option value="">Select a product</option>
                {products.map(product => (
                  <option key={product.id} value={product.id}>
                    {product.name} ({product.sku})
                  </option>
                ))}
              </select>
            </div>

            {[
              { key: 'current_stock', label: 'Current Stock', type: 'number', min: '0', placeholder: '5' },
              { key: 'minimum_stock', label: 'Minimum Stock', type: 'number', min: '0', placeholder: '10' },
              { key: 'average_daily_sales', label: 'Avg Daily Sales', type: 'number', min: '0', step: '0.1', placeholder: '3.5' },
            ].map(({ key, label, type, min, placeholder, step }) => (
              <div key={key} className="form-group">
                <label className="form-label">{label}</label>
                <input
                  type={type}
                  min={min}
                  step={step}
                  className="form-input"
                  placeholder={placeholder}
                  value={reorderData[key]}
                  onChange={e => setReorderData(d => ({ ...d, [key]: e.target.value }))}
                  required
                />
              </div>
            ))}

            <button
              id="reorder-submit"
              type="submit"
              className="btn btn-primary w-full"
              style={{ justifyContent: 'center' }}
              disabled={reorderLoading}
            >
              {reorderLoading ? 'Calculating...' : '⚡ Get Suggestion'}
            </button>
          </form>

          {reorderError && (
            <div className="form-error" role="alert" style={{ marginTop: 14 }}>
              {reorderError}
            </div>
          )}

          {reorderResult && (
            <div style={{ marginTop: 16, background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 'var(--radius-md)', padding: 16 }}>
              <div className="flex-between" style={{ marginBottom: 12 }}>
                <span style={{ fontWeight: 700 }}>Reorder Quantity</span>
                <span style={{ fontSize: 28, fontWeight: 800, color: 'var(--color-accent-light)' }}>
                  {reorderResult.reorder_quantity}
                </span>
              </div>
              <div className="flex-between" style={{ marginBottom: 12 }}>
                <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Urgency</span>
                <span className={`badge ${urgencyConfig[reorderResult.urgency]?.cls ?? 'badge-neutral'}`}>
                  {urgencyConfig[reorderResult.urgency]?.label ?? reorderResult.urgency}
                </span>
              </div>
              {reorderResult.days_until_stockout !== null && (
                <div className="flex-between" style={{ marginBottom: 12 }}>
                  <span style={{ fontSize: 13, color: 'var(--color-text-muted)' }}>Days until stockout</span>
                  <span style={{ fontSize: 14, fontWeight: 600 }}>{reorderResult.days_until_stockout}d</span>
                </div>
              )}
              <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', lineHeight: 1.6, borderTop: '1px solid var(--color-border)', paddingTop: 10, marginTop: 10 }}>
                {reorderResult.recommendation}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Low Stock Products */}
      {lowStockProducts && lowStockProducts.length > 0 && (
        <div className="card">
          <div className="p-6" style={{ paddingBottom: 16 }}>
            <h2 style={{ fontSize: 18, fontWeight: 700 }}>⚠ Products Needing Attention</h2>
          </div>
          <div className="table-wrapper" style={{ border: 'none', borderTop: '1px solid var(--color-border)', borderRadius: 0 }}>
            <table>
              <thead>
                <tr><th>Product</th><th>SKU</th><th>Qty</th><th>Min</th><th>Status</th></tr>
              </thead>
              <tbody>
                {lowStockProducts.map(p => (
                  <tr key={p.id}>
                    <td style={{ fontWeight: 600 }}>{p.name}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--color-accent-light)' }}>{p.sku}</td>
                    <td style={{ fontWeight: 700, color: 'var(--color-warning)' }}>{p.quantity}</td>
                    <td style={{ color: 'var(--color-text-muted)' }}>{p.minimum_stock}</td>
                    <td>
                      <span className="badge badge-warning">● Low Stock</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
