import { useState, useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { inventoryApi } from '../api/inventoryApi';
import { useAuth } from '../context/AuthContext';

const DEFAULT_OFFER_FORM = {
  name: '',
  campaign_id: '',
  discount_type: 'percentage',
  discount_value: '15',
  starts_at: '',
  ends_at: '',
  minimum_purchase: '0',
  maximum_discount: '',
  priority: '1',
  product_ids: [],
  category_ids: [],
  subcategory_ids: [],
};

export default function Offers() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const canManage = ['admin', 'manager'].includes(user?.role);

  // UI state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [form, setForm] = useState(DEFAULT_OFFER_FORM);
  const [productSearch, setProductSearch] = useState('');

  // Live Pricing Test Widget state
  const [testProductId, setTestProductId] = useState('');
  const [testPurchaseAmount, setTestPurchaseAmount] = useState('');

  // Queries
  const { data: offers = [], isLoading } = useQuery({
    queryKey: ['offers'],
    queryFn: () => inventoryApi.listOffers().then((res) => res.data),
  });

  const { data: campaigns = [] } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => inventoryApi.listCampaigns().then((res) => res.data),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => inventoryApi.listCategories().then((res) => res.data),
  });

  const { data: subcategories = [] } = useQuery({
    queryKey: ['subcategories'],
    queryFn: () => inventoryApi.listSubcategories().then((res) => res.data),
  });

  const { data: products = [] } = useQuery({
    queryKey: ['product-options'],
    queryFn: () => inventoryApi.listProductOptions().then((res) => res.data),
  });

  // Dynamic test pricing query
  const { data: testPricing, isFetching: testPricingLoading } = useQuery({
    queryKey: ['product-pricing-test', testProductId, testPurchaseAmount],
    queryFn: () =>
      inventoryApi
        .getProductPricing(
          testProductId,
          testPurchaseAmount ? Number(testPurchaseAmount) : undefined
        )
        .then((res) => res.data),
    enabled: Boolean(testProductId),
    staleTime: 5000,
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (payload) => inventoryApi.createOffer(payload),
    onSuccess: () => {
      setForm(DEFAULT_OFFER_FORM);
      setShowCreateForm(false);
      qc.invalidateQueries({ queryKey: ['offers'] });
    },
  });

  const disableMutation = useMutation({
    mutationFn: (id) => inventoryApi.disableOffer(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['offers'] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => inventoryApi.deleteOffer(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['offers'] }),
  });

  // KPIs
  const activeOffers = offers.filter((o) => o.status === 'active');
  const scheduledOffers = offers.filter((o) => o.status === 'scheduled');
  const disabledOffers = offers.filter((o) => o.status === 'disabled');

  // Filtered offers list
  const filteredOffers = useMemo(() => {
    return offers.filter((o) => {
      if (statusFilter !== 'ALL' && o.status?.toLowerCase() !== statusFilter.toLowerCase()) {
        return false;
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchName = o.name?.toLowerCase().includes(term);
        const matchCamp = campaigns.find((c) => c.id === o.campaign_id)?.name?.toLowerCase().includes(term);
        return matchName || matchCamp;
      }
      return true;
    });
  }, [offers, statusFilter, searchTerm, campaigns]);

  const filteredProducts = useMemo(() => {
    if (!productSearch) return products.slice(0, 30);
    const term = productSearch.toLowerCase();
    return products.filter((p) => p.name?.toLowerCase().includes(term) || p.sku?.toLowerCase().includes(term));
  }, [products, productSearch]);

  const handleCreateSubmit = (e) => {
    e.preventDefault();
    createMutation.mutate({
      name: form.name.trim(),
      campaign_id: form.campaign_id ? Number(form.campaign_id) : undefined,
      discount_type: form.discount_type,
      discount_value: Number(form.discount_value),
      minimum_purchase: Number(form.minimum_purchase || 0),
      maximum_discount: form.maximum_discount ? Number(form.maximum_discount) : undefined,
      priority: Number(form.priority || 0),
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: new Date(form.ends_at).toISOString(),
      product_ids: form.product_ids,
      category_ids: form.category_ids,
      subcategory_ids: form.subcategory_ids,
      is_enabled: true,
    });
  };

  const toggleProductSelect = (id) => {
    setForm((prev) => ({
      ...prev,
      product_ids: prev.product_ids.includes(id)
        ? prev.product_ids.filter((p) => p !== id)
        : [...prev.product_ids, id],
    }));
  };

  const toggleCategorySelect = (id) => {
    setForm((prev) => ({
      ...prev,
      category_ids: prev.category_ids.includes(id)
        ? prev.category_ids.filter((c) => c !== id)
        : [...prev.category_ids, id],
    }));
  };

  const toggleSubcategorySelect = (id) => {
    setForm((prev) => ({
      ...prev,
      subcategory_ids: prev.subcategory_ids.includes(id)
        ? prev.subcategory_ids.filter((s) => s !== id)
        : [...prev.subcategory_ids, id],
    }));
  };

  return (
    <div className="page-content fade-in">
      {/* Page Header */}
      <div className="page-header inventory-header">
        <div>
          <h1 className="page-title">Festive & Promotional Offers</h1>
          <p className="page-subtitle">
            Manage priority-based pricing rules, percentage & fixed discounts, and targeted promotions.
          </p>
        </div>
        {canManage && (
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? '✕ Close Form' : '＋ New Offer'}
          </button>
        )}
      </div>

      {/* KPI Cards */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon-wrap" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>%</span>
            <span className="stat-label">Total Offers</span>
          </div>
          <div className="stat-value">{offers.length}</div>
          <div className="stat-trend neutral">All pricing rules</div>
        </div>
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon-wrap" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>●</span>
            <span className="stat-label">Active (Live)</span>
          </div>
          <div className="stat-value" style={{ color: '#34d399' }}>{activeOffers.length}</div>
          <div className="stat-trend positive">Applying to catalog</div>
        </div>
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon-wrap" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>⏱</span>
            <span className="stat-label">Scheduled</span>
          </div>
          <div className="stat-value">{scheduledOffers.length}</div>
          <div className="stat-trend neutral">Future validity</div>
        </div>
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon-wrap" style={{ background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8' }}>⏸</span>
            <span className="stat-label">Disabled / Paused</span>
          </div>
          <div className="stat-value">{disabledOffers.length}</div>
          <div className="stat-trend neutral">Inactive rules</div>
        </div>
      </div>

      {/* Create Offer Panel */}
      {showCreateForm && canManage && (
        <form className="card p-6 mb-6" onSubmit={handleCreateSubmit} style={{ border: '1px solid rgba(16, 185, 129, 0.3)', marginBottom: 24 }}>
          <div className="section-header-row" style={{ marginBottom: 16 }}>
            <div>
              <h2 className="section-title">Create Promotional Offer</h2>
              <p className="page-subtitle" style={{ fontSize: 13 }}>Configure discount values, priorities, and target product scopes.</p>
            </div>
            <span className="pill success">New Rule</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
            <div className="form-group">
              <label className="form-label">Offer Name *</label>
              <input
                className="form-input"
                required
                placeholder="e.g. 15% Festive Flat Discount on Laptops"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Link to Campaign (Optional)</label>
              <select
                className="form-select"
                value={form.campaign_id}
                onChange={(e) => setForm({ ...form, campaign_id: e.target.value })}
              >
                <option value="">No Campaign (Standalone Offer)</option>
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.status})
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Discount Type</label>
              <div style={{ display: 'flex', gap: 8 }}>
                <button
                  type="button"
                  className={`chip-btn ${form.discount_type === 'percentage' ? 'active' : ''}`}
                  style={{ flex: 1, justifyContent: 'center' }}
                  onClick={() => setForm({ ...form, discount_type: 'percentage' })}
                >
                  % Percentage
                </button>
                <button
                  type="button"
                  className={`chip-btn ${form.discount_type === 'fixed' ? 'active' : ''}`}
                  style={{ flex: 1, justifyContent: 'center' }}
                  onClick={() => setForm({ ...form, discount_type: 'fixed' })}
                >
                  $ Fixed Amount
                </button>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">
                Discount Value {form.discount_type === 'percentage' ? '(%)' : '($)'} *
              </label>
              <input
                className="form-input"
                required
                type="number"
                min="0.01"
                step="0.01"
                placeholder={form.discount_type === 'percentage' ? '15' : '100'}
                value={form.discount_value}
                onChange={(e) => setForm({ ...form, discount_value: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Starts At *</label>
              <input
                className="form-input"
                required
                type="datetime-local"
                value={form.starts_at}
                onChange={(e) => setForm({ ...form, starts_at: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Ends At *</label>
              <input
                className="form-input"
                required
                type="datetime-local"
                value={form.ends_at}
                onChange={(e) => setForm({ ...form, ends_at: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Priority Level</label>
              <input
                className="form-input"
                type="number"
                min="0"
                placeholder="0 = Normal, higher overrides other offers"
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Minimum Purchase ($)</label>
              <input
                className="form-input"
                type="number"
                min="0"
                step="0.01"
                placeholder="0 = No minimum"
                value={form.minimum_purchase}
                onChange={(e) => setForm({ ...form, minimum_purchase: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Maximum Discount Cap ($)</label>
              <input
                className="form-input"
                type="number"
                min="0"
                step="0.01"
                placeholder="Optional ceiling limit"
                value={form.maximum_discount}
                onChange={(e) => setForm({ ...form, maximum_discount: e.target.value })}
              />
            </div>

            {/* Target Scopes */}
            <div className="card p-4" style={{ gridColumn: '1 / -1', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--color-border)' }}>
              <div style={{ fontWeight: 600, marginBottom: 12 }}>
                🎯 Target Categories & Products ({form.category_ids.length} categories, {form.product_ids.length} products)
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 16 }}>
                <div>
                  <label className="form-label" style={{ fontSize: 12, fontWeight: 600 }}>Categories</label>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, maxHeight: 120, overflowY: 'auto', padding: 8, background: 'rgba(0,0,0,0.2)', borderRadius: 6 }}>
                    {categories.map((cat) => {
                      const isSelected = form.category_ids.includes(cat.id);
                      return (
                        <button
                          key={cat.id}
                          type="button"
                          onClick={() => toggleCategorySelect(cat.id)}
                          className={`chip-btn ${isSelected ? 'active' : ''}`}
                          style={{ fontSize: 11 }}
                        >
                          {isSelected ? '✓ ' : '+ '} {cat.name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <label className="form-label" style={{ fontSize: 12, fontWeight: 600 }}>Specific Products</label>
                  <input
                    type="text"
                    className="form-input"
                    placeholder="Search products..."
                    value={productSearch}
                    onChange={(e) => setProductSearch(e.target.value)}
                    style={{ fontSize: 12, padding: '4px 8px', marginBottom: 6 }}
                  />
                  <div style={{ maxHeight: 100, overflowY: 'auto', border: '1px solid var(--color-border)', borderRadius: 6, padding: 4, background: 'rgba(0,0,0,0.2)' }}>
                    {filteredProducts.map((p) => {
                      const isChecked = form.product_ids.includes(p.id);
                      return (
                        <label
                          key={p.id}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            padding: '4px 6px',
                            cursor: 'pointer',
                            fontSize: 12,
                            background: isChecked ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => toggleProductSelect(p.id)}
                          />
                          <span style={{ flex: 1 }}>{p.name}</span>
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {createMutation.isError && (
            <div className="form-error" style={{ marginTop: 14 }}>
              {createMutation.error?.response?.data?.detail || 'Failed to create offer.'}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 12, marginTop: 18 }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowCreateForm(false)}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createMutation.isPending}
            >
              {createMutation.isPending ? 'Saving Offer...' : '✓ Create Offer'}
            </button>
          </div>
        </form>
      )}

      {/* Live Pricing Test Sandbox */}
      <div className="card p-5 mb-6" style={{ background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(16, 185, 129, 0.05) 100%)', border: '1px solid rgba(99, 102, 241, 0.2)', marginBottom: 24 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
          <div>
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
              <span>⚡ Live Pricing Engine Simulator</span>
              <span className="pill info" style={{ fontSize: 11 }}>Real-time API</span>
            </h2>
            <p className="page-subtitle" style={{ fontSize: 12, margin: '4px 0 0 0' }}>
              Select any electronic product to test how active campaigns and priority offers affect checkout pricing.
            </p>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 12, alignItems: 'end' }}>
          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: 12 }}>Test Product</label>
            <select
              className="form-select"
              value={testProductId}
              onChange={(e) => setTestProductId(e.target.value)}
            >
              <option value="">Select a Product to test</option>
              {products.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} · {p.sku} (${p.price})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group" style={{ margin: 0 }}>
            <label className="form-label" style={{ fontSize: 12 }}>Purchase Amount / Cart Total ($)</label>
            <input
              className="form-input"
              type="number"
              min="0"
              step="0.01"
              placeholder="Optional cart value"
              value={testPurchaseAmount}
              onChange={(e) => setTestPurchaseAmount(e.target.value)}
            />
          </div>

          {testProductId && testPricing && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 16,
                padding: '8px 16px',
                background: 'rgba(0, 0, 0, 0.3)',
                borderRadius: 'var(--radius-sm)',
                border: '1px solid var(--color-border)',
              }}
            >
              <div>
                <small style={{ color: 'var(--color-text-muted)', display: 'block', fontSize: 10 }}>Original</small>
                <span style={{ textDecoration: 'line-through', color: 'var(--color-text-muted)', fontWeight: 600 }}>
                  ${Number(testPricing.original_price).toFixed(2)}
                </span>
              </div>
              <div style={{ fontSize: 20, color: '#34d399' }}>→</div>
              <div>
                <small style={{ color: '#34d399', display: 'block', fontSize: 10, fontWeight: 700 }}>
                  {testPricing.offer_name ? `Offer: ${testPricing.offer_name}` : 'Final Price'}
                </small>
                <span style={{ fontSize: 20, fontWeight: 800, color: '#34d399' }}>
                  ${Number(testPricing.final_price).toFixed(2)}
                </span>
              </div>
              {testPricing.discount_amount > 0 && (
                <span className="pill success" style={{ fontSize: 11, marginLeft: 'auto' }}>
                  Saved ${Number(testPricing.discount_amount).toFixed(2)} ({testPricing.discount_percentage}%)
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Offers List Table */}
      <div className="card">
        <div className="card-header-row" style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, fontSize: 16 }}>All Offers</span>
            <div style={{ display: 'flex', gap: 6, marginLeft: 12 }}>
              {['ALL', 'ACTIVE', 'SCHEDULED', 'EXPIRED', 'DISABLED'].map((st) => (
                <button
                  key={st}
                  onClick={() => setStatusFilter(st)}
                  className={`chip-btn ${statusFilter === st ? 'active' : ''}`}
                  style={{ fontSize: 12, padding: '4px 10px' }}
                >
                  {st}
                </button>
              ))}
            </div>
          </div>
          <div className="search-wrapper" style={{ maxWidth: 260 }}>
            <span className="search-icon">⌕</span>
            <input
              type="text"
              className="search-input"
              placeholder="Search offers..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ padding: '6px 12px 6px 32px', fontSize: 13 }}
            />
          </div>
        </div>

        {isLoading ? (
          <div className="loader-box flex-center" style={{ minHeight: 200 }}>
            <div className="spinner spinner-lg" />
          </div>
        ) : filteredOffers.length === 0 ? (
          <div className="empty-state" style={{ padding: 48, textAlign: 'center' }}>
            <span style={{ fontSize: 36 }}>%</span>
            <p style={{ marginTop: 12, color: 'var(--color-text-muted)' }}>No promotional offers found.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Offer & Linked Campaign</th>
                  <th>Discount Value</th>
                  <th>Validity Period</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredOffers.map((o) => {
                  const campaign = campaigns.find((c) => c.id === o.campaign_id);
                  const isLive = o.status === 'active';
                  const isScheduled = o.status === 'scheduled';
                  const isDisabled = o.status === 'disabled';
                  return (
                    <tr key={o.id}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{o.name}</div>
                        {campaign ? (
                          <span className="pill info" style={{ fontSize: 11, marginTop: 4, display: 'inline-block' }}>
                            ◈ {campaign.name}
                          </span>
                        ) : (
                          <small className="table-subcategory" style={{ color: 'var(--color-text-muted)' }}>
                            Standalone Offer
                          </small>
                        )}
                      </td>
                      <td>
                        <span style={{ fontSize: 15, fontWeight: 700, color: 'var(--color-accent-light)' }}>
                          {o.discount_type === 'percentage' ? `${o.discount_value}% OFF` : `$${Number(o.discount_value).toFixed(2)} OFF`}
                        </span>
                        {o.minimum_purchase > 0 && (
                          <div style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                            Min purchase: ${o.minimum_purchase}
                          </div>
                        )}
                      </td>
                      <td>
                        <div style={{ fontSize: 13 }}>
                          {new Date(o.starts_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          {' → '}
                          {new Date(o.ends_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </div>
                      </td>
                      <td>
                        <span className="pill neutral" style={{ fontWeight: 600, fontSize: 12 }}>
                          P-{o.priority}
                        </span>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            isLive
                              ? 'badge-success'
                              : isScheduled
                              ? 'badge-warning'
                              : isDisabled
                              ? 'badge-neutral'
                              : 'badge-danger'
                          }`}
                        >
                          {isLive ? '● Live' : isScheduled ? '⏱ Scheduled' : isDisabled ? '⏸ Disabled' : 'Expired'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="action-group" style={{ justifyContent: 'flex-end' }}>
                          {canManage && isLive && (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => disableMutation.mutate(o.id)}
                              disabled={disableMutation.isPending}
                              title="Pause / disable this offer"
                            >
                              Pause
                            </button>
                          )}
                          {canManage && (
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => {
                                if (window.confirm(`Permanently delete offer "${o.name}"?`)) {
                                  deleteMutation.mutate(o.id);
                                }
                              }}
                              disabled={deleteMutation.isPending}
                              title="Delete offer"
                            >
                              🗑️
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
