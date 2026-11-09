import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { inventoryApi } from '../api/inventoryApi';
import { useAuth } from '../context/AuthContext';
import { StatCard } from '../components/ui/StatCard';

const STATUS_TABS = [
  { value: 'all', label: 'All Requests' },
  { value: 'recommendations', label: '🚨 Required Reorders' },
  { value: 'PENDING', label: 'Pending Approval' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'ORDERED', label: 'In Transit / Ordered' },
  { value: 'RECEIVED', label: 'Partially Received' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'REJECTED', label: 'Rejected' },
];

export default function Reorders() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const navigate = useNavigate();

  const role = user?.role?.toLowerCase();
  const isAdmin = role === 'admin';
  const isManager = role === 'manager';
  const canApprove = isAdmin || isManager;
  const canCreate = isAdmin || isManager;

  const [activeTab, setActiveTab] = useState('recommendations');
  const [search, setSearch] = useState('');

  // Modals state
  const [createModalData, setCreateModalData] = useState(null); // { product, ... }
  const [rejectModalData, setRejectModalData] = useState(null); // { request }
  const [poModalData, setPoModalData] = useState(null); // { request }
  const [rejectionReason, setRejectionReason] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Form state for creating reorder
  const [requestedQty, setRequestedQty] = useState(20);
  const [selectedSupplierId, setSelectedSupplierId] = useState('');
  const [reorderReason, setReorderReason] = useState('');

  // Form state for creating PO from reorder
  const [poWarehouseId, setPoWarehouseId] = useState('1');
  const [poExpectedDelivery, setPoExpectedDelivery] = useState('');
  const [poUnitCost, setPoUnitCost] = useState('');

  // Queries
  const { data: summary, refetch: refetchSummary } = useQuery({
    queryKey: ['reorders-summary'],
    queryFn: () => inventoryApi.getReorderSummary().then((r) => r.data),
    staleTime: 15000,
  });

  const { data: recommendations = [], isLoading: loadingRecs, refetch: refetchRecs } = useQuery({
    queryKey: ['reorders-required'],
    queryFn: () => inventoryApi.getRequiredReorders().then((r) => r.data),
    staleTime: 15000,
  });

  const { data: reordersList = [], isLoading: loadingRequests, refetch: refetchRequests } = useQuery({
    queryKey: ['reorders-list'],
    queryFn: () => inventoryApi.listReorders().then((r) => r.data),
    staleTime: 15000,
  });

  const { data: suppliers = [] } = useQuery({
    queryKey: ['suppliers'],
    queryFn: () => inventoryApi.listSuppliers().then((r) => r.data),
    staleTime: 60000,
  });

  const { data: warehouses = [] } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => inventoryApi.listWarehouses().then((r) => r.data),
    staleTime: 60000,
  });

  const refreshAll = () => {
    refetchSummary();
    refetchRecs();
    refetchRequests();
  };

  // Mutations
  const createMutation = useMutation({
    mutationFn: (payload) => inventoryApi.createReorder(payload),
    onSuccess: () => {
      setSuccessMessage('Reorder request submitted successfully (Status: PENDING)');
      setCreateModalData(null);
      refreshAll();
      setTimeout(() => setSuccessMessage(''), 4000);
    },
    onError: (err) => {
      setErrorMessage(err?.response?.data?.detail || err.message || 'Failed to create reorder request');
    },
  });

  const approveMutation = useMutation({
    mutationFn: (id) => inventoryApi.approveReorder(id),
    onSuccess: () => {
      setSuccessMessage('Reorder request APPROVED. You can now generate a Purchase Order.');
      refreshAll();
      setTimeout(() => setSuccessMessage(''), 4000);
    },
    onError: (err) => {
      setErrorMessage(err?.response?.data?.detail || err.message || 'Approval failed');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: ({ id, reason }) => inventoryApi.rejectReorder(id, reason),
    onSuccess: () => {
      setSuccessMessage('Reorder request REJECTED.');
      setRejectModalData(null);
      setRejectionReason('');
      refreshAll();
      setTimeout(() => setSuccessMessage(''), 4000);
    },
    onError: (err) => {
      setErrorMessage(err?.response?.data?.detail || err.message || 'Rejection failed');
    },
  });

  const poMutation = useMutation({
    mutationFn: ({ id, payload }) => inventoryApi.createPOFromReorder(id, payload),
    onSuccess: ({ data }) => {
      setSuccessMessage(`Purchase Order created: ${data.po_number} (Status: ORDERED)`);
      setPoModalData(null);
      refreshAll();
      setTimeout(() => {
        setSuccessMessage('');
        navigate('/purchase-orders');
      }, 1500);
    },
    onError: (err) => {
      setErrorMessage(err?.response?.data?.detail || err.message || 'Failed to create Purchase Order');
    },
  });

  // Open Create Modal
  const openCreateModal = (item) => {
    setErrorMessage('');
    setCreateModalData(item);
    setRequestedQty(item.reorder_quantity || 20);
    setSelectedSupplierId(item.supplier_id ? String(item.supplier_id) : suppliers[0]?.id ? String(suppliers[0].id) : '');
    setReorderReason(`Stock level (${item.current_stock || item.quantity}) is at/below reorder point (${item.reorder_point || 10}).`);
  };

  // Open PO Modal
  const openPoModal = (req) => {
    setErrorMessage('');
    setPoModalData(req);
    setPoWarehouseId(warehouses[0]?.id ? String(warehouses[0].id) : '1');
    setPoExpectedDelivery('');
    setPoUnitCost(req.product?.unit_cost || '');
  };

  // Filtering data
  const filteredRecs = useMemo(() => {
    return recommendations.filter((r) => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        r.product_name?.toLowerCase().includes(q) ||
        r.sku?.toLowerCase().includes(q) ||
        r.supplier_name?.toLowerCase().includes(q)
      );
    });
  }, [recommendations, search]);

  const filteredRequests = useMemo(() => {
    return reordersList.filter((r) => {
      if (activeTab !== 'all' && r.status !== activeTab) return false;
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        r.product_name?.toLowerCase().includes(q) ||
        r.sku?.toLowerCase().includes(q) ||
        r.supplier_name?.toLowerCase().includes(q) ||
        r.po_number?.toLowerCase().includes(q)
      );
    });
  }, [reordersList, activeTab, search]);

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'REQUIRED': return 'pill danger';
      case 'PENDING': return 'pill warning';
      case 'APPROVED': return 'pill info';
      case 'ORDERED': return 'pill purple';
      case 'RECEIVED': return 'pill cyan';
      case 'COMPLETED': return 'pill success';
      case 'REJECTED': return 'pill neutral';
      default: return 'pill neutral';
    }
  };

  return (
    <div className="page-content fade-in reorder-page">
      {/* Header */}
      <div className="page-header flex-between">
        <div>
          <span className="eyebrow">Smart Replenishment Engine</span>
          <h1 className="page-title">Reorder Management</h1>
          <p className="page-subtitle">
            Automated reorder point detection, manager review workflow, and purchase order fulfillment.
          </p>
        </div>
        <div className="header-actions">
          <Link to="/purchase-orders" className="btn btn-secondary">
            📦 View Purchase Orders
          </Link>
          <Link to="/suppliers" className="btn btn-secondary">
            🏢 Manage Suppliers
          </Link>
        </div>
      </div>

      {/* Notifications */}
      {successMessage && (
        <div className="card alert-box success fade-in" style={{ padding: '12px 18px', marginBottom: 20 }}>
          <span>✓ {successMessage}</span>
        </div>
      )}
      {errorMessage && (
        <div className="card alert-box danger fade-in" style={{ padding: '12px 18px', marginBottom: 20 }}>
          <span>⚠ {errorMessage}</span>
          <button className="btn-close" onClick={() => setErrorMessage('')}>×</button>
        </div>
      )}

      {/* KPI Stats Grid */}
      <div className="stats-grid premium-stats" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', marginBottom: 24 }}>
        <StatCard
          icon="🚨"
          label="Products to Reorder"
          value={summary?.products_requiring_reorder ?? recommendations.length}
          iconBg="rgba(239,68,68,0.18)"
          trend={summary?.products_requiring_reorder ? -1 : 0}
          trendLabel="Stock ≤ Reorder Point"
        />
        <StatCard
          icon="⏳"
          label="Pending Requests"
          value={summary?.pending_requests ?? reordersList.filter(r => r.status === 'PENDING').length}
          iconBg="rgba(245,158,11,0.18)"
          trendLabel="Awaiting approval"
        />
        <StatCard
          icon="✓"
          label="Approved Requests"
          value={summary?.approved_requests ?? reordersList.filter(r => r.status === 'APPROVED').length}
          iconBg="rgba(91,124,255,0.18)"
          trendLabel="Ready for PO"
        />
        <StatCard
          icon="🚚"
          label="Orders in Transit"
          value={summary?.orders_in_transit ?? reordersList.filter(r => r.status === 'ORDERED').length}
          iconBg="rgba(139,92,246,0.18)"
          trendLabel="PO issued"
        />
        <StatCard
          icon="📦"
          label="Completed Reorders"
          value={summary?.recently_received_stock ?? reordersList.filter(r => r.status === 'COMPLETED').length}
          iconBg="rgba(30,201,139,0.18)"
          trendLabel="Stock received"
        />
      </div>

      {/* Filter / Tabs Bar */}
      <div className="card p-6 filter-panel" style={{ marginBottom: 20 }}>
        <div className="filter-row flex-between" style={{ flexWrap: 'wrap', gap: 12 }}>
          <div className="search-wrapper" style={{ flex: 1, minWidth: 260 }}>
            <span className="search-icon">⌕</span>
            <input
              type="text"
              className="search-input"
              placeholder="Search product, SKU, supplier, or PO #..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button className="btn btn-secondary btn-sm" onClick={refreshAll} title="Refresh data">
            ↻ Refresh
          </button>
        </div>

        <div className="stock-tab-row" style={{ marginTop: 16, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {STATUS_TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setActiveTab(tab.value)}
              className={`chip-btn ${activeTab === tab.value ? 'active' : ''}`}
            >
              {tab.label}
              {tab.value === 'recommendations' && recommendations.length > 0 && (
                <span className="badge-count" style={{ marginLeft: 6, background: '#ef4444', color: '#fff', padding: '2px 6px', borderRadius: 10, fontSize: '0.75rem' }}>
                  {recommendations.length}
                </span>
              )}
              {tab.value === 'PENDING' && (
                <span className="badge-count" style={{ marginLeft: 6, background: 'rgba(245,158,11,0.3)', color: '#f7b955', padding: '2px 6px', borderRadius: 10, fontSize: '0.75rem' }}>
                  {reordersList.filter(r => r.status === 'PENDING').length}
                </span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Content Section: Recommendations vs Requests Table */}
      {activeTab === 'recommendations' ? (
        <div className="card inventory-table-card">
          <div className="section-header-row table-header p-6" style={{ borderBottom: '1px solid var(--line)' }}>
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0 }}>
                Products Requiring Reorder (Stock ≤ Reorder Point)
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '4px 0 0' }}>
                System automatically detects products requiring replenishment based on configured thresholds.
              </p>
            </div>
            <span className="pill danger">{filteredRecs.length} Products</span>
          </div>

          {loadingRecs ? (
            <div className="flex-center loader-box p-8"><div className="spinner spinner-lg" /></div>
          ) : filteredRecs.length === 0 ? (
            <div className="empty-state large p-8">
              <span>✓</span>
              <p>All products have healthy stock levels above their reorder points.</p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Current Stock</th>
                    <th>Reorder Point</th>
                    <th>Order Qty</th>
                    <th>Supplier</th>
                    <th>Status</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRecs.map((item) => (
                    <tr key={item.product_id}>
                      <td>
                        <Link to={`/inventory/${item.product_id}`} className="link-strong">
                          {item.product_name}
                        </Link>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                          {item.sku} {item.category_name && `· ${item.category_name}`}
                        </div>
                      </td>
                      <td>
                        <span className="qty-value out_of_stock" style={{ fontWeight: 700, color: item.current_stock === 0 ? '#ff5d7a' : '#f7b955' }}>
                          {item.current_stock}
                        </span>
                      </td>
                      <td className="muted-cell">{item.reorder_point}</td>
                      <td className="bold-cell" style={{ color: '#5b7cff' }}>
                        +{item.reorder_quantity}
                      </td>
                      <td>
                        {item.supplier_name ? (
                          <span className="pill neutral" style={{ fontSize: '0.8rem' }}>🏢 {item.supplier_name}</span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Not assigned</span>
                        )}
                      </td>
                      <td>
                        <span className={getStatusBadgeClass(item.status)}>
                          {item.has_active_request ? `In Workflow (${item.active_reorder_status})` : 'Reorder Needed'}
                        </span>
                      </td>
                      <td>
                        {item.has_active_request ? (
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => {
                              setActiveTab(item.active_reorder_status || 'all');
                            }}
                          >
                            View #{item.active_reorder_request_id}
                          </button>
                        ) : canCreate ? (
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => openCreateModal(item)}
                          >
                            ⚡ Create Request
                          </button>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>View only</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        /* Reorder Requests Table */
        <div className="card inventory-table-card">
          <div className="section-header-row table-header p-6" style={{ borderBottom: '1px solid var(--line)' }}>
            <div>
              <h2 style={{ fontSize: '1.15rem', fontWeight: 600, margin: 0 }}>
                {activeTab === 'all' ? 'All Reorder Requests' : `${activeTab} Reorder Requests`}
              </h2>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', margin: '4px 0 0' }}>
                Track request review, manager approvals, PO fulfillment, and stock delivery history.
              </p>
            </div>
            <span className="pill info">{filteredRequests.length} Requests</span>
          </div>

          {loadingRequests ? (
            <div className="flex-center loader-box p-8"><div className="spinner spinner-lg" /></div>
          ) : filteredRequests.length === 0 ? (
            <div className="empty-state large p-8">
              <span>📋</span>
              <p>No reorder requests found for this status.</p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Req #</th>
                    <th>Product</th>
                    <th>Current / Min</th>
                    <th>Requested Qty</th>
                    <th>Supplier</th>
                    <th>Status</th>
                    <th>Reason / Approver</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredRequests.map((req) => (
                    <tr key={req.id}>
                      <td className="mono-cell" style={{ fontWeight: 600 }}>#{req.id}</td>
                      <td>
                        <Link to={`/inventory/${req.product_id}`} className="link-strong">
                          {req.product_name}
                        </Link>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>
                          {req.sku}
                        </div>
                      </td>
                      <td className="muted-cell">
                        {req.current_stock} / {req.reorder_point}
                      </td>
                      <td className="bold-cell" style={{ color: '#5b7cff', fontSize: '0.95rem' }}>
                        +{req.requested_quantity}
                      </td>
                      <td>
                        {req.supplier_name ? (
                          <span className="pill neutral" style={{ fontSize: '0.8rem' }}>🏢 {req.supplier_name}</span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>Default</span>
                        )}
                      </td>
                      <td>
                        <span className={getStatusBadgeClass(req.status)}>
                          {req.status}
                        </span>
                        {req.po_number && (
                          <div style={{ marginTop: 4 }}>
                            <Link to="/purchase-orders" style={{ fontSize: '0.75rem', color: '#63d4ff', fontFamily: 'monospace' }}>
                              {req.po_number}
                            </Link>
                          </div>
                        )}
                      </td>
                      <td>
                        <div style={{ fontSize: '0.8rem', maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {req.reorder_reason || 'Standard restock'}
                        </div>
                        {req.rejection_reason && (
                          <div style={{ fontSize: '0.75rem', color: 'var(--danger)', marginTop: 2 }}>
                            Rejection: {req.rejection_reason}
                          </div>
                        )}
                        {req.approved_by && (
                          <small style={{ color: 'var(--text-muted)', fontSize: '0.72rem' }}>
                            Reviewed by UID #{req.approved_by}
                          </small>
                        )}
                      </td>
                      <td>
                        <div className="action-group">
                          {req.status === 'PENDING' && canApprove && (
                            <>
                              <button
                                className="btn btn-primary btn-sm"
                                disabled={approveMutation.isPending}
                                onClick={() => approveMutation.mutate(req.id)}
                                title="Approve Request"
                              >
                                ✓ Approve
                              </button>
                              <button
                                className="btn btn-danger btn-sm"
                                onClick={() => {
                                  setRejectModalData(req);
                                  setRejectionReason('');
                                }}
                                title="Reject Request"
                              >
                                ✕ Reject
                              </button>
                            </>
                          )}

                          {req.status === 'APPROVED' && canCreate && (
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => openPoModal(req)}
                              title="Create Purchase Order"
                            >
                              📄 Create PO
                            </button>
                          )}

                          {(req.status === 'ORDERED' || req.status === 'RECEIVED') && (
                            <Link to="/purchase-orders" className="btn btn-secondary btn-sm">
                              📦 Track PO
                            </Link>
                          )}

                          {req.status === 'COMPLETED' && (
                            <span className="pill success" style={{ fontSize: '0.75rem' }}>Completed</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* ── CREATE REORDER REQUEST MODAL ────────────────────────────────────── */}
      {createModalData && (
        <div className="modal-overlay fade-in" onClick={() => setCreateModalData(null)}>
          <div className="modal-box card p-6" style={{ maxWidth: 540 }} onClick={(e) => e.stopPropagation()}>
            <div className="flex-between" style={{ marginBottom: 16 }}>
              <h2 className="modal-title" style={{ margin: 0 }}>Create Reorder Request</h2>
              <button className="btn-close" onClick={() => setCreateModalData(null)}>×</button>
            </div>

            <div style={{ background: 'var(--panel-soft)', padding: '12px 16px', borderRadius: 'var(--radius-md)', marginBottom: 20 }}>
              <div style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text)' }}>
                {createModalData.product_name || createModalData.name}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontFamily: 'monospace', marginTop: 2 }}>
                SKU: {createModalData.sku}
              </div>
              <div style={{ display: 'flex', gap: 20, marginTop: 10, fontSize: '0.85rem' }}>
                <div>Current Stock: <strong style={{ color: '#f7b955' }}>{createModalData.current_stock ?? createModalData.quantity ?? 0}</strong></div>
                <div>Reorder Point: <strong>{createModalData.reorder_point || 10}</strong></div>
                <div>Default Qty: <strong style={{ color: '#5b7cff' }}>{createModalData.reorder_quantity || 20}</strong></div>
              </div>
            </div>

            <form onSubmit={(e) => {
              e.preventDefault();
              createMutation.mutate({
                product_id: createModalData.product_id || createModalData.id,
                requested_quantity: parseInt(requestedQty, 10),
                supplier_id: selectedSupplierId ? parseInt(selectedSupplierId, 10) : undefined,
                reorder_reason: reorderReason,
              });
            }}>
              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">Requested Quantity * (Editable)</label>
                <input
                  type="number"
                  min="1"
                  className="form-input"
                  value={requestedQty}
                  onChange={(e) => setRequestedQty(e.target.value)}
                  required
                />
                <small className="form-hint" style={{ color: 'var(--text-muted)' }}>
                  Pre-filled with product reorder quantity. You can adjust it as required.
                </small>
              </div>

              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">Supplier</label>
                <select
                  className="form-select"
                  value={selectedSupplierId}
                  onChange={(e) => setSelectedSupplierId(e.target.value)}
                >
                  <option value="">Select a supplier...</option>
                  {suppliers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} {s.contact_person ? `(${s.contact_person})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: 20 }}>
                <label className="form-label">Reorder Reason / Notes</label>
                <textarea
                  rows={3}
                  className="form-textarea"
                  value={reorderReason}
                  onChange={(e) => setReorderReason(e.target.value)}
                  placeholder="Reason for triggering reorder..."
                />
              </div>

              <div className="flex-between gap-3">
                <button type="button" className="btn btn-secondary" onClick={() => setCreateModalData(null)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={createMutation.isPending || !requestedQty || requestedQty <= 0}
                >
                  {createMutation.isPending ? 'Submitting...' : '✓ Submit Reorder Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── REJECT REQUEST MODAL ────────────────────────────────────────────── */}
      {rejectModalData && (
        <div className="modal-overlay fade-in" onClick={() => setRejectModalData(null)}>
          <div className="modal-box card p-6" style={{ maxWidth: 480 }} onClick={(e) => e.stopPropagation()}>
            <div className="flex-between" style={{ marginBottom: 16 }}>
              <h2 className="modal-title" style={{ margin: 0, color: 'var(--danger)' }}>Reject Reorder Request #{rejectModalData.id}</h2>
              <button className="btn-close" onClick={() => setRejectModalData(null)}>×</button>
            </div>

            <p style={{ color: 'var(--text-soft)', fontSize: '0.9rem', marginBottom: 16 }}>
              Please specify the mandatory reason for rejecting this replenishment request for{' '}
              <strong>{rejectModalData.product_name}</strong>.
            </p>

            <form onSubmit={(e) => {
              e.preventDefault();
              if (!rejectionReason.trim()) {
                setErrorMessage('Rejection reason is required');
                return;
              }
              rejectMutation.mutate({ id: rejectModalData.id, reason: rejectionReason });
            }}>
              <div className="form-group" style={{ marginBottom: 20 }}>
                <label className="form-label">Rejection Reason *</label>
                <textarea
                  rows={4}
                  className="form-textarea"
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="e.g., Sufficient buffer in alternative warehouse, or budget constraints."
                  required
                />
              </div>

              <div className="flex-between gap-3">
                <button type="button" className="btn btn-secondary" onClick={() => setRejectModalData(null)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-danger"
                  disabled={rejectMutation.isPending || !rejectionReason.trim()}
                >
                  {rejectMutation.isPending ? 'Rejecting...' : 'Confirm Rejection'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── CREATE PURCHASE ORDER MODAL ─────────────────────────────────────── */}
      {poModalData && (
        <div className="modal-overlay fade-in" onClick={() => setPoModalData(null)}>
          <div className="modal-box card p-6" style={{ maxWidth: 540 }} onClick={(e) => e.stopPropagation()}>
            <div className="flex-between" style={{ marginBottom: 16 }}>
              <h2 className="modal-title" style={{ margin: 0 }}>Create Purchase Order</h2>
              <button className="btn-close" onClick={() => setPoModalData(null)}>×</button>
            </div>

            <div style={{ background: 'var(--panel-soft)', padding: '12px 16px', borderRadius: 'var(--radius-md)', marginBottom: 20 }}>
              <div style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text)' }}>
                {poModalData.product_name}
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-soft)', marginTop: 4 }}>
                Approved Reorder Request: <strong>#{poModalData.id}</strong> · Qty: <strong style={{ color: '#5b7cff' }}>{poModalData.requested_quantity}</strong>
              </div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: 2 }}>
                Supplier: {poModalData.supplier_name || 'Standard Supplier'}
              </div>
            </div>

            <form onSubmit={(e) => {
              e.preventDefault();
              poMutation.mutate({
                id: poModalData.id,
                payload: {
                  warehouse_id: parseInt(poWarehouseId, 10),
                  expected_delivery: poExpectedDelivery || undefined,
                  unit_cost: poUnitCost ? parseFloat(poUnitCost) : undefined,
                },
              });
            }}>
              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">Destination Warehouse *</label>
                <select
                  className="form-select"
                  value={poWarehouseId}
                  onChange={(e) => setPoWarehouseId(e.target.value)}
                  required
                >
                  {warehouses.map((w) => (
                    <option key={w.id} value={w.id}>
                      {w.name} ({w.warehouse_code})
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">Expected Delivery Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={poExpectedDelivery}
                  onChange={(e) => setPoExpectedDelivery(e.target.value)}
                />
              </div>

              <div className="form-group" style={{ marginBottom: 20 }}>
                <label className="form-label">Unit Cost ($)</label>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  className="form-input"
                  placeholder="Optional override"
                  value={poUnitCost}
                  onChange={(e) => setPoUnitCost(e.target.value)}
                />
              </div>

              <div className="flex-between gap-3">
                <button type="button" className="btn btn-secondary" onClick={() => setPoModalData(null)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={poMutation.isPending}
                >
                  {poMutation.isPending ? 'Issuing PO...' : '🚀 Issue Purchase Order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
