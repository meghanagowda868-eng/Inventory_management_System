import { useState, useMemo } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { inventoryApi } from '../api/inventoryApi';
import { useAuth } from '../context/AuthContext';

const DEFAULT_FORM = {
  name: '',
  description: '',
  banner_title: '',
  festival_event_id: '',
  starts_at: '',
  ends_at: '',
  minimum_discount: '10',
  maximum_discount: '25',
  selected_discount: '15',
};

export default function Campaigns() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const canManage = ['admin', 'manager'].includes(user?.role);

  // UI state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState(null);
  const [applyingCampaign, setApplyingCampaign] = useState(null);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');
  const [form, setForm] = useState(DEFAULT_FORM);

  // Apply modal state
  const [applyDiscount, setApplyDiscount] = useState('15');
  const [selectedProductIds, setSelectedProductIds] = useState([]);
  const [selectedCategoryIds, setSelectedCategoryIds] = useState([]);
  const [productSearch, setProductSearch] = useState('');

  // Queries
  const { data: campaigns = [], isLoading } = useQuery({
    queryKey: ['campaigns'],
    queryFn: () => inventoryApi.listCampaigns().then((res) => res.data),
  });

  const { data: events = [] } = useQuery({
    queryKey: ['seasonal-events'],
    queryFn: () => inventoryApi.listSeasonalEvents().then((res) => res.data),
  });

  const { data: products = [] } = useQuery({
    queryKey: ['product-options'],
    queryFn: () => inventoryApi.listProductOptions().then((res) => res.data),
  });

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => inventoryApi.listCategories().then((res) => res.data),
  });

  // Mutations
  const createMutation = useMutation({
    mutationFn: (payload) => inventoryApi.createCampaign(payload),
    onSuccess: () => {
      setForm(DEFAULT_FORM);
      setShowCreateForm(false);
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }) => inventoryApi.updateCampaign(id, payload),
    onSuccess: () => {
      setEditingCampaign(null);
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => inventoryApi.deleteCampaign(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaigns'] });
    },
  });

  const applyDiscountMutation = useMutation({
    mutationFn: ({ campaignId, data }) => inventoryApi.applyCampaignDiscount(campaignId, data),
    onSuccess: () => {
      setApplyingCampaign(null);
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      qc.invalidateQueries({ queryKey: ['offers'] });
    },
  });

  // KPIs
  const activeCount = campaigns.filter((c) => c.status === 'active').length;
  const scheduledCount = campaigns.filter((c) => c.status === 'scheduled').length;
  const highestDiscount = campaigns.reduce((max, c) => Math.max(max, c.maximum_discount || 0), 0);

  // Filtered campaigns
  const filteredCampaigns = useMemo(() => {
    return campaigns.filter((c) => {
      if (statusFilter !== 'ALL' && c.status?.toLowerCase() !== statusFilter.toLowerCase()) {
        return false;
      }
      if (searchTerm) {
        const term = searchTerm.toLowerCase();
        const matchName = c.name?.toLowerCase().includes(term);
        const matchDesc = c.description?.toLowerCase().includes(term);
        const festival = events.find((e) => e.id === c.festival_event_id);
        const matchFestival = festival?.name?.toLowerCase().includes(term);
        return matchName || matchDesc || matchFestival;
      }
      return true;
    });
  }, [campaigns, statusFilter, searchTerm, events]);

  // Handle festival selection in create form (auto-populates default dates & name)
  const handleFestivalChange = (eventId) => {
    const selected = events.find((e) => e.id === Number(eventId));
    if (selected) {
      setForm((prev) => ({
        ...prev,
        festival_event_id: String(selected.id),
        name: `${selected.name} Super Saver Campaign`,
        banner_title: `Grand ${selected.name} Electronics Festival Sale`,
        starts_at: `${selected.start_date}T00:00`,
        ends_at: `${selected.end_date}T23:59`,
      }));
    } else {
      setForm((prev) => ({ ...prev, festival_event_id: '' }));
    }
  };

  const handleCreateSubmit = (e) => {
    e.preventDefault();
    createMutation.mutate({
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      banner_title: form.banner_title.trim() || undefined,
      festival_event_id: form.festival_event_id ? Number(form.festival_event_id) : undefined,
      minimum_discount: Number(form.minimum_discount),
      maximum_discount: Number(form.maximum_discount),
      selected_discount: Number(form.selected_discount),
      starts_at: new Date(form.starts_at).toISOString(),
      ends_at: new Date(form.ends_at).toISOString(),
      is_enabled: true,
    });
  };

  const handleEditSubmit = (e) => {
    e.preventDefault();
    updateMutation.mutate({
      id: editingCampaign.id,
      payload: {
        name: editingCampaign.name.trim(),
        description: editingCampaign.description?.trim() || undefined,
        banner_title: editingCampaign.banner_title?.trim() || undefined,
        minimum_discount: Number(editingCampaign.minimum_discount),
        maximum_discount: Number(editingCampaign.maximum_discount),
        selected_discount: Number(editingCampaign.selected_discount),
        starts_at: editingCampaign.starts_at ? new Date(editingCampaign.starts_at).toISOString() : undefined,
        ends_at: editingCampaign.ends_at ? new Date(editingCampaign.ends_at).toISOString() : undefined,
      },
    });
  };

  const openApplyModal = (campaign) => {
    setApplyingCampaign(campaign);
    setApplyDiscount(String(campaign.selected_discount ?? campaign.minimum_discount ?? '15'));
    setSelectedProductIds([]);
    setSelectedCategoryIds([]);
    setProductSearch('');
  };

  const handleApplyConfirm = (e) => {
    e.preventDefault();
    if (!selectedProductIds.length && !selectedCategoryIds.length) return;
    applyDiscountMutation.mutate({
      campaignId: applyingCampaign.id,
      data: {
        selected_discount: Number(applyDiscount),
        product_ids: selectedProductIds,
        category_ids: selectedCategoryIds,
        subcategory_ids: [],
      },
    });
  };

  const toggleProductSelect = (id) => {
    setSelectedProductIds((prev) =>
      prev.includes(id) ? prev.filter((p) => p !== id) : [...prev, id]
    );
  };

  const toggleCategorySelect = (id) => {
    setSelectedCategoryIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  };

  const filteredProducts = useMemo(() => {
    if (!productSearch) return products.slice(0, 40);
    const term = productSearch.toLowerCase();
    return products.filter((p) => p.name?.toLowerCase().includes(term) || p.sku?.toLowerCase().includes(term));
  }, [products, productSearch]);

  return (
    <div className="page-content fade-in">
      {/* Header */}
      <div className="page-header inventory-header">
        <div>
          <h1 className="page-title">Festive Campaigns</h1>
          <p className="page-subtitle">
            Create and manage seasonal marketing campaigns, set discount bounds, and activate promotional deals.
          </p>
        </div>
        {canManage && (
          <button
            className="btn btn-primary"
            onClick={() => setShowCreateForm(!showCreateForm)}
          >
            {showCreateForm ? '✕ Close Form' : '＋ New Campaign'}
          </button>
        )}
      </div>

      {/* KPI Cards */}
      <div className="stats-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', marginBottom: 24 }}>
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon-wrap" style={{ background: 'rgba(99, 102, 241, 0.15)', color: '#818cf8' }}>◈</span>
            <span className="stat-label">Total Campaigns</span>
          </div>
          <div className="stat-value">{campaigns.length}</div>
          <div className="stat-trend neutral">All promotional records</div>
        </div>
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon-wrap" style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>●</span>
            <span className="stat-label">Active (Live)</span>
          </div>
          <div className="stat-value" style={{ color: '#34d399' }}>{activeCount}</div>
          <div className="stat-trend positive">Running now</div>
        </div>
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon-wrap" style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>◒</span>
            <span className="stat-label">Scheduled</span>
          </div>
          <div className="stat-value">{scheduledCount}</div>
          <div className="stat-trend neutral">Upcoming festivals</div>
        </div>
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-icon-wrap" style={{ background: 'rgba(236, 72, 153, 0.15)', color: '#f472b6' }}>%</span>
            <span className="stat-label">Max Discount Cap</span>
          </div>
          <div className="stat-value">{highestDiscount}%</div>
          <div className="stat-trend neutral">Configured ceiling</div>
        </div>
      </div>

      {/* Create Campaign Panel */}
      {showCreateForm && canManage && (
        <form className="card p-6 mb-6" onSubmit={handleCreateSubmit} style={{ border: '1px solid rgba(99, 102, 241, 0.3)', marginBottom: 24 }}>
          <div className="section-header-row" style={{ marginBottom: 16 }}>
            <div>
              <h2 className="section-title">Create Festive Campaign</h2>
              <p className="page-subtitle" style={{ fontSize: 13 }}>Configure time bounds and manager-approved discount guardrails.</p>
            </div>
            <span className="pill info">Draft Mode</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 16 }}>
            <div className="form-group">
              <label className="form-label">Link to Festival Event</label>
              <select
                className="form-select"
                value={form.festival_event_id}
                onChange={(e) => handleFestivalChange(e.target.value)}
              >
                <option value="">Select a Festival (Auto-fills dates)</option>
                {events.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.name} ({ev.start_date.slice(0, 4)}) · {ev.start_date} to {ev.end_date}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Campaign Name *</label>
              <input
                className="form-input"
                required
                placeholder="e.g. Diwali Super Electronics Sale"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Banner / Tagline</label>
              <input
                className="form-input"
                placeholder="e.g. Up to 25% off Top Laptops & Tech"
                value={form.banner_title}
                onChange={(e) => setForm({ ...form, banner_title: e.target.value })}
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

            <div className="form-group" style={{ gridColumn: '1 / -1' }}>
              <label className="form-label">Description</label>
              <textarea
                className="form-input"
                rows={2}
                placeholder="Strategic notes or promotion context..."
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>

            {/* Discount Policy Guardrails */}
            <div className="card p-4" style={{ gridColumn: '1 / -1', background: 'rgba(255, 255, 255, 0.02)', border: '1px solid var(--color-border)' }}>
              <div style={{ fontWeight: 600, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
                <span>🛡️ Discount Guardrails & Manager Policy</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, alignItems: 'center' }}>
                <div className="form-group">
                  <label className="form-label">Minimum Discount (%)</label>
                  <input
                    className="form-input"
                    type="number"
                    min="0"
                    max="100"
                    step="0.5"
                    value={form.minimum_discount}
                    onChange={(e) => setForm({ ...form, minimum_discount: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Maximum Discount (%)</label>
                  <input
                    className="form-input"
                    type="number"
                    min={form.minimum_discount || 0}
                    max="100"
                    step="0.5"
                    value={form.maximum_discount}
                    onChange={(e) => setForm({ ...form, maximum_discount: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">
                    Default Selected: <strong>{form.selected_discount}%</strong>
                  </label>
                  <input
                    type="range"
                    min={form.minimum_discount || 0}
                    max={form.maximum_discount || 100}
                    step="0.5"
                    value={form.selected_discount}
                    onChange={(e) => setForm({ ...form, selected_discount: e.target.value })}
                    style={{ width: '100%', marginTop: 8 }}
                  />
                </div>
              </div>
            </div>
          </div>

          {createMutation.isError && (
            <div className="form-error" style={{ marginTop: 14 }}>
              {createMutation.error?.response?.data?.detail || 'Failed to create campaign.'}
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
              {createMutation.isPending ? 'Saving Campaign...' : '✓ Create Campaign'}
            </button>
          </div>
        </form>
      )}

      {/* Campaign List Table */}
      <div className="card">
        <div className="card-header-row" style={{ padding: '16px 20px', borderBottom: '1px solid var(--color-border)' }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, fontSize: 16 }}>All Campaigns</span>
            <div style={{ display: 'flex', gap: 6, marginLeft: 12 }}>
              {['ALL', 'ACTIVE', 'SCHEDULED', 'EXPIRED'].map((st) => (
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
              placeholder="Search campaigns..."
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
        ) : filteredCampaigns.length === 0 ? (
          <div className="empty-state" style={{ padding: 48, textAlign: 'center' }}>
            <span style={{ fontSize: 36 }}>◈</span>
            <p style={{ marginTop: 12, color: 'var(--color-text-muted)' }}>No campaigns matching your criteria.</p>
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Campaign & Description</th>
                  <th>Festival Event</th>
                  <th>Discount Window</th>
                  <th>Schedule</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredCampaigns.map((c) => {
                  const festival = events.find((e) => e.id === c.festival_event_id);
                  const isLive = c.status === 'active';
                  const isScheduled = c.status === 'scheduled';
                  return (
                    <tr key={c.id}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--color-text-primary)' }}>{c.name}</div>
                        {c.banner_title && (
                          <div style={{ fontSize: 12, color: 'var(--color-accent-light)' }}>{c.banner_title}</div>
                        )}
                        {c.description && (
                          <small className="table-subcategory" style={{ color: 'var(--color-text-muted)' }}>
                            {c.description}
                          </small>
                        )}
                      </td>
                      <td>
                        {festival ? (
                          <span className="pill info" style={{ fontSize: 12 }}>
                            🎉 {festival.name} ({festival.start_date.slice(0, 4)})
                          </span>
                        ) : (
                          <span style={{ color: 'var(--color-text-muted)', fontSize: 13 }}>General</span>
                        )}
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>
                          {c.minimum_discount ?? 0}% – {c.maximum_discount ?? 0}%
                        </div>
                        <small className="table-subcategory">
                          Selected: <strong>{c.selected_discount ?? '—'}%</strong>
                        </small>
                      </td>
                      <td>
                        <div style={{ fontSize: 13 }}>
                          {new Date(c.starts_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                          {' → '}
                          {new Date(c.ends_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                        </div>
                      </td>
                      <td>
                        <span
                          className={`badge ${
                            isLive ? 'badge-success' : isScheduled ? 'badge-warning' : 'badge-neutral'
                          }`}
                        >
                          {isLive ? '● Live' : isScheduled ? '⏱ Scheduled' : 'Expired'}
                        </span>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="action-group" style={{ justifyContent: 'flex-end' }}>
                          {canManage && (
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => openApplyModal(c)}
                              title="Apply this campaign discount to products or categories"
                            >
                              ⚡ Apply Discount
                            </button>
                          )}
                          {canManage && (
                            <button
                              className="btn btn-secondary btn-sm"
                              onClick={() => setEditingCampaign({ ...c })}
                              title="Edit campaign settings"
                            >
                              ✏️ Edit
                            </button>
                          )}
                          {canManage && (
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => {
                                if (window.confirm(`Permanently delete campaign "${c.name}"?`)) {
                                  deleteMutation.mutate(c.id);
                                }
                              }}
                              disabled={deleteMutation.isPending}
                              title="Delete campaign"
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

      {/* Apply Discount Modal */}
      {applyingCampaign && (
        <div className="modal-overlay" onClick={() => setApplyingCampaign(null)}>
          <div
            className="modal-box"
            style={{ maxWidth: 650, maxHeight: '90vh', overflowY: 'auto' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex-between" style={{ marginBottom: 12 }}>
              <h2 className="modal-title" style={{ margin: 0 }}>
                Apply Campaign Discount
              </h2>
              <span className="pill info">
                Bounds: {applyingCampaign.minimum_discount}% – {applyingCampaign.maximum_discount}%
              </span>
            </div>
            <p className="modal-copy" style={{ marginBottom: 16 }}>
              Applying this campaign creates an active festive offer for the selected items without altering base catalog costs.
            </p>

            <form onSubmit={handleApplyConfirm}>
              {/* Discount Selector */}
              <div className="form-group" style={{ marginBottom: 16 }}>
                <div className="flex-between">
                  <label className="form-label" style={{ fontWeight: 600 }}>
                    Discount Percentage
                  </label>
                  <span style={{ fontSize: 18, fontWeight: 800, color: 'var(--color-accent-light)' }}>
                    {applyDiscount}%
                  </span>
                </div>
                <input
                  type="range"
                  min={applyingCampaign.minimum_discount ?? 0}
                  max={applyingCampaign.maximum_discount ?? 100}
                  step="0.5"
                  value={applyDiscount}
                  onChange={(e) => setApplyDiscount(e.target.value)}
                  style={{ width: '100%' }}
                />
              </div>

              {/* Target Categories */}
              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label" style={{ fontWeight: 600 }}>
                  Apply to Entire Categories ({selectedCategoryIds.length} selected)
                </label>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, maxHeight: 100, overflowY: 'auto', padding: 8, background: 'rgba(255, 255, 255, 0.02)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--color-border)' }}>
                  {categories.map((cat) => {
                    const isSelected = selectedCategoryIds.includes(cat.id);
                    return (
                      <button
                        key={cat.id}
                        type="button"
                        onClick={() => toggleCategorySelect(cat.id)}
                        className={`chip-btn ${isSelected ? 'active' : ''}`}
                        style={{ fontSize: 12 }}
                      >
                        {isSelected ? '✓ ' : '+ '} {cat.name}
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Target Products */}
              <div className="form-group" style={{ marginBottom: 16 }}>
                <div className="flex-between" style={{ marginBottom: 6 }}>
                  <label className="form-label" style={{ fontWeight: 600, margin: 0 }}>
                    Apply to Specific Products ({selectedProductIds.length} selected)
                  </label>
                  {selectedProductIds.length > 0 && (
                    <button
                      type="button"
                      className="text-link"
                      style={{ fontSize: 12 }}
                      onClick={() => setSelectedProductIds([])}
                    >
                      Clear selected ({selectedProductIds.length})
                    </button>
                  )}
                </div>
                <input
                  type="text"
                  className="form-input mb-2"
                  placeholder="Filter products by name or SKU..."
                  value={productSearch}
                  onChange={(e) => setProductSearch(e.target.value)}
                  style={{ fontSize: 13, marginBottom: 8 }}
                />
                <div
                  style={{
                    maxHeight: 180,
                    overflowY: 'auto',
                    border: '1px solid var(--color-border)',
                    borderRadius: 'var(--radius-sm)',
                    background: 'rgba(0, 0, 0, 0.2)',
                  }}
                >
                  {filteredProducts.map((p) => {
                    const isChecked = selectedProductIds.includes(p.id);
                    return (
                      <label
                        key={p.id}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 10,
                          padding: '6px 12px',
                          borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
                          cursor: 'pointer',
                          background: isChecked ? 'rgba(99, 102, 241, 0.1)' : 'transparent',
                        }}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={() => toggleProductSelect(p.id)}
                        />
                        <span style={{ fontSize: 13, flex: 1 }}>{p.name}</span>
                        <span className="mono-cell" style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                          {p.sku}
                        </span>
                      </label>
                    );
                  })}
                </div>
              </div>

              {applyDiscountMutation.isError && (
                <div className="form-error" style={{ marginBottom: 14 }}>
                  {applyDiscountMutation.error?.response?.data?.detail || 'Could not apply campaign discount.'}
                </div>
              )}

              <div className="flex-center gap-3" style={{ justifyContent: 'flex-end', marginTop: 20 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setApplyingCampaign(null)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={
                    applyDiscountMutation.isPending ||
                    (!selectedProductIds.length && !selectedCategoryIds.length)
                  }
                >
                  {applyDiscountMutation.isPending ? 'Activating Offer...' : '✓ Confirm & Activate Offer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Campaign Modal */}
      {editingCampaign && (
        <div className="modal-overlay" onClick={() => setEditingCampaign(null)}>
          <div className="modal-box" style={{ maxWidth: 550 }} onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Edit Campaign</h2>
            <form onSubmit={handleEditSubmit}>
              <div className="form-group mb-3">
                <label className="form-label">Campaign Name</label>
                <input
                  className="form-input"
                  required
                  value={editingCampaign.name}
                  onChange={(e) => setEditingCampaign({ ...editingCampaign, name: e.target.value })}
                />
              </div>
              <div className="form-group mb-3">
                <label className="form-label">Banner Title</label>
                <input
                  className="form-input"
                  value={editingCampaign.banner_title || ''}
                  onChange={(e) => setEditingCampaign({ ...editingCampaign, banner_title: e.target.value })}
                />
              </div>
              <div className="form-group mb-3">
                <label className="form-label">Description</label>
                <textarea
                  className="form-input"
                  rows={2}
                  value={editingCampaign.description || ''}
                  onChange={(e) => setEditingCampaign({ ...editingCampaign, description: e.target.value })}
                />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 }}>
                <div className="form-group">
                  <label className="form-label">Min Discount (%)</label>
                  <input
                    className="form-input"
                    type="number"
                    min="0"
                    max="100"
                    value={editingCampaign.minimum_discount || 0}
                    onChange={(e) => setEditingCampaign({ ...editingCampaign, minimum_discount: e.target.value })}
                  />
                </div>
                <div className="form-group">
                  <label className="form-label">Max Discount (%)</label>
                  <input
                    className="form-input"
                    type="number"
                    min={editingCampaign.minimum_discount || 0}
                    max="100"
                    value={editingCampaign.maximum_discount || 0}
                    onChange={(e) => setEditingCampaign({ ...editingCampaign, maximum_discount: e.target.value })}
                  />
                </div>
              </div>
              <div className="flex-center gap-3" style={{ justifyContent: 'flex-end', marginTop: 18 }}>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => setEditingCampaign(null)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={updateMutation.isPending}
                >
                  {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
