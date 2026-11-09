import { useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { inventoryApi } from '../api/inventoryApi';
import { aiApi } from '../api/aiApi';
import StockBadge from '../components/inventory/StockBadge';
import { useAuth } from '../context/AuthContext';

export default function ProductDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();

  const [delta, setDelta] = useState('');
  const [reason, setReason] = useState('');
  const [aiPrediction, setAiPrediction] = useState(null);
  const [predicting, setPredicting] = useState(false);

  const { data: product, isLoading } = useQuery({
    queryKey: ['product', id],
    queryFn: () => inventoryApi.getProduct(id).then(r => r.data),
  });
  const { data: pricing } = useQuery({
    queryKey: ['product-pricing', id],
    queryFn: () => inventoryApi.getProductPricing(id).then(r => r.data),
    enabled: Boolean(product),
    staleTime: 30000,
  });

  const stockMutation = useMutation({
    mutationFn: ({ delta, reason }) => inventoryApi.adjustStock(id, parseInt(delta, 10), reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['product', id] });
      qc.invalidateQueries({ queryKey: ['products'] });
      qc.invalidateQueries({ queryKey: ['reorders-required'] });
      qc.invalidateQueries({ queryKey: ['reorders-summary'] });
      setDelta('');
      setReason('');
    },
  });

  const handlePredictDemand = async () => {
    if (!product) return;
    setPredicting(true);
    try {
      const { data } = await aiApi.predictDemand({
        product_id: product.id,
        product_name: product.name,
        category: product.category || 'default',
        current_quantity: product.quantity,
        price: product.price,
      });
      setAiPrediction(data);
    } catch {
      setAiPrediction(null);
    } finally {
      setPredicting(false);
    }
  };

  const canEdit = ['admin', 'manager'].includes(user?.role?.toLowerCase());

  if (isLoading) return (
    <div className="page-content flex-center" style={{ minHeight: 400 }}>
      <div className="spinner spinner-lg" />
    </div>
  );

  if (!product) return (
    <div className="page-content flex-center" style={{ minHeight: 400, flexDirection: 'column', gap: 12 }}>
      <span style={{ fontSize: 48 }}>🚫</span>
      <p>Product not found</p>
      <Link to="/inventory" className="btn btn-secondary">Back to Inventory</Link>
    </div>
  );

  const isReorderNeeded = product.quantity <= (product.reorder_point ?? 10);

  return (
    <div className="page-content fade-in product-detail-shell">
      <div className="crumbs">
        <Link to="/inventory">Inventory</Link>
        <span>›</span>
        <span>{product.name}</span>
      </div>

      <div className="detail-grid">
        <div>
          <div className="card p-6 detail-card">
            <div className="product-header-row">
              <div>
                <div className="eyebrow subtle">Product overview</div>
                <h1 className="detail-title">{product.name}</h1>
                <p className="mono-muted">{product.sku}</p>
              </div>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                {isReorderNeeded && (
                  <span className="pill danger" title="Stock at or below reorder threshold">
                    🚨 Reorder Triggered
                  </span>
                )}
                <StockBadge status={product.stock_status} />
              </div>
            </div>

            <div className="detail-stats-grid">
              {[
                ['Category', product.category_name || product.category || '—'],
                ['Subcategory', product.subcategory_name || '—'],
                ['Selling Price', pricing?.offer_id ? (
                  <span><s>${Number(pricing.original_price).toFixed(2)}</s> <strong className="promo-price">${Number(pricing.final_price).toFixed(2)}</strong></span>
                ) : `$${Number(product.price).toFixed(2)}`],
                ['Unit Cost', product.unit_cost ? `$${Number(product.unit_cost).toFixed(2)}` : '—'],
                ['Current Quantity', product.quantity],
                ['Min Stock Alert', product.minimum_stock],
                ['⚡ Reorder Point', product.reorder_point ?? 10],
                ['⚡ Reorder Qty', `+${product.reorder_quantity ?? 20}`],
                ['Primary Supplier', product.supplier_name || '—'],
                ['Brand', product.brand || '—'],
                ['Model', product.model_number || '—'],
                ['Barcode', product.barcode || '—'],
              ].map(([label, value]) => (
                <div key={label} className="mini-stat-box">
                  <div className="meta-key">{label}</div>
                  <div className="meta-value">{value}</div>
                </div>
              ))}
            </div>

            {pricing?.offer_id && (
              <div className="promotion-note">
                <strong>{pricing.offer_name}</strong>
                <span>{pricing.discount_type === 'percentage' ? `${pricing.discount_value}% off` : `$${pricing.discount_value} off`} · Active offer</span>
              </div>
            )}

            {product.description && (
              <div className="description-block">
                <div className="meta-key">Description</div>
                <p>{product.description}</p>
              </div>
            )}

            <div className="detail-actions" style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              {isReorderNeeded && canEdit && (
                <Link to="/reorders" className="btn btn-primary">
                  ⚡ Go to Reorder Desk
                </Link>
              )}
              {canEdit && (
                <Link to={`/inventory/${id}/edit`} className="btn btn-secondary">
                  Edit Product
                </Link>
              )}
              <Link to="/inventory" className="btn btn-secondary">
                Back to inventory
              </Link>
            </div>
          </div>

          {canEdit && (
            <div className="card p-6 detail-card compact-card" style={{ marginTop: 20 }}>
              <h2 className="section-title">Adjust stock</h2>
              <div className="stock-adjust-row">
                <div className="form-group compact-field">
                  <label className="form-label">Delta (+ or -)</label>
                  <input id="stock-delta" type="number" className="form-input" placeholder="+10 or -5" value={delta} onChange={(e) => setDelta(e.target.value)} />
                </div>
                <div className="form-group compact-field">
                  <label className="form-label">Reason</label>
                  <input type="text" className="form-input" placeholder="e.g. Audit correction" value={reason} onChange={(e) => setReason(e.target.value)} />
                </div>
              </div>
              <button className="btn btn-primary" disabled={!delta || stockMutation.isPending} onClick={() => stockMutation.mutate({ delta, reason })}>
                {stockMutation.isPending ? 'Adjusting...' : 'Apply adjustment'}
              </button>
              {stockMutation.isSuccess && <p className="success-note">✓ Stock updated successfully</p>}
            </div>
          )}
        </div>

        <div className="card p-6 ai-panel">
          <div className="section-header-row table-header">
            <h2>AI demand prediction</h2>
            <span className="pill info">AI</span>
          </div>
          <p className="panel-copy">Forecast demand, highlight risk, and guide restock timing with real product context.</p>

          <button id="predict-demand-btn" className="btn btn-primary w-full" onClick={handlePredictDemand} disabled={predicting}>
            {predicting ? 'Analyzing…' : 'Predict demand'}
          </button>

          {aiPrediction && (
            <div className="ai-result-box">
              <div className="ai-metric-row">
                <span>Demand level</span>
                <span className={`badge ${aiPrediction.demand_level === 'high' ? 'badge-success' : aiPrediction.demand_level === 'medium' ? 'badge-warning' : 'badge-neutral'}`}>
                  {aiPrediction.demand_level}
                </span>
              </div>

              <div className="ai-metric-row">
                <span>Confidence</span>
                <strong>{aiPrediction.confidence_percentage}%</strong>
              </div>

              <div className="confidence-bar">
                <div className="confidence-fill" style={{ width: `${aiPrediction.confidence_percentage}%` }} />
              </div>

              <div className="ai-number-block">
                <div className="meta-key">Predicted daily sales</div>
                <div className="big-number">{aiPrediction.predicted_daily_sales}</div>
              </div>

              <div className="reasoning-box">{aiPrediction.reasoning}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
