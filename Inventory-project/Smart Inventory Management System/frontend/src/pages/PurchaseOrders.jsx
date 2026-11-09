import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { inventoryApi } from '../api/inventoryApi';
import { useAuth } from '../context/AuthContext';
import { StatCard } from '../components/ui/StatCard';

const PO_STATUS_FILTERS = [
  { value: '', label: 'All Orders' },
  { value: 'ORDERED', label: 'In Transit / Ordered' },
  { value: 'PARTIALLY_RECEIVED', label: 'Partially Received' },
  { value: 'RECEIVED', label: 'Fully Received' },
  { value: 'PENDING_APPROVAL', label: 'Pending Approval' },
  { value: 'CANCELLED', label: 'Cancelled' },
];

export default function PurchaseOrders() {
  const { user } = useAuth();
  const qc = useQueryClient();

  const role = user?.role?.toLowerCase();
  const isAdmin = role === 'admin';
  const isManager = role === 'manager';
  const canOperate = isAdmin || isManager;

  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  // Modals state
  const [receiveModalData, setReceiveModalData] = useState(null); // { order }
  const [receiveInputs, setReceiveInputs] = useState({}); // { productId: qty }
  const [detailsModalData, setDetailsModalData] = useState(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  // Direct PO creation state
  const [selectedSupplierId, setSelectedSupplierId] = useState('');
  const [selectedWarehouseId, setSelectedWarehouseId] = useState('1');
  const [poExpectedDate, setPoExpectedDate] = useState('');
  const [poItems, setPoItems] = useState([{ product_id: '', quantity: 10, unit_cost: '' }]);

  const [successMessage, setSuccessMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');

  // Queries
  const { data: orders = [], isLoading: loadingOrders, refetch: refetchOrders } = useQuery({
    queryKey: ['purchase-orders', statusFilter],
    queryFn: () => inventoryApi.listPurchaseOrders(statusFilter ? { status: statusFilter } : undefined).then((r) => r.data),
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

  const { data: products = [] } = useQuery({
    queryKey: ['products-options'],
    queryFn: () => inventoryApi.listProductOptions().then((r) => r.data),
    staleTime: 60000,
  });

  // Mutations
  const receiveMutation = useMutation({
    mutationFn: ({ id, payload }) => inventoryApi.receivePurchaseOrder(id, payload),
    onSuccess: () => {
      setSuccessMessage('Stock successfully received! Inventory counts and stock ledger updated.');
      setReceiveModalData(null);
      refetchOrders();
      qc.invalidateQueries({ queryKey: ['products'] });
      qc.invalidateQueries({ queryKey: ['reorders-summary'] });
      qc.invalidateQueries({ queryKey: ['reorders-required'] });
      setTimeout(() => setSuccessMessage(''), 4000);
    },
    onError: (err) => {
      setErrorMessage(err?.response?.data?.detail || err.message || 'Stock receipt failed');
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id) => inventoryApi.cancelPurchaseOrder(id),
    onSuccess: () => {
      setSuccessMessage('Purchase order has been cancelled.');
      refetchOrders();
      setTimeout(() => setSuccessMessage(''), 4000);
    },
    onError: (err) => {
      setErrorMessage(err?.response?.data?.detail || err.message || 'Failed to cancel order');
    },
  });

  const createOrderMutation = useMutation({
    mutationFn: (payload) => inventoryApi.createPurchaseOrder(payload),
    onSuccess: ({ data }) => {
      setSuccessMessage(`Purchase Order created: ${data.po_number}`);
      setCreateModalOpen(false);
      refetchOrders();
      setTimeout(() => setSuccessMessage(''), 4000);
    },
    onError: (err) => {
      setErrorMessage(err?.response?.data?.detail || err.message || 'Failed to create order');
    },
  });

  // Open Receive Modal
  const openReceiveModal = (order) => {
    setErrorMessage('');
    setReceiveModalData(order);
    const initial = {};
    order.items.forEach((item) => {
      const rem = item.quantity - item.received_quantity;
      initial[item.product_id] = rem > 0 ? rem : 0;
    });
    setReceiveInputs(initial);
  };

  const handleReceiveSubmit = (e) => {
    e.preventDefault();
    if (!receiveModalData) return;

    const itemsToReceive = receiveModalData.items
      .map((it) => ({
        product_id: it.product_id,
        received_quantity: parseInt(receiveInputs[it.product_id] || 0, 10),
      }))
      .filter((it) => it.received_quantity > 0);

    if (itemsToReceive.length === 0) {
      setErrorMessage('Please enter at least 1 unit to receive.');
      return;
    }

    receiveMutation.mutate({
      id: receiveModalData.id,
      payload: { items: itemsToReceive },
    });
  };

  const filteredOrders = useMemo(() => {
    return orders.filter((o) => {
      if (!search) return true;
      const q = search.toLowerCase();
      return (
        o.po_number?.toLowerCase().includes(q) ||
        o.supplier_name?.toLowerCase().includes(q) ||
        o.warehouse_name?.toLowerCase().includes(q) ||
        o.items?.some((it) => it.product_name?.toLowerCase().includes(q) || it.sku?.toLowerCase().includes(q))
      );
    });
  }, [orders, search]);

  const getStatusBadge = (status) => {
    switch (status) {
      case 'ORDERED': return <span className="pill purple">🚚 Ordered / In Transit</span>;
      case 'PARTIALLY_RECEIVED': return <span className="pill cyan">⏳ Partially Received</span>;
      case 'RECEIVED': return <span className="pill success">✓ Received</span>;
      case 'PENDING_APPROVAL': return <span className="pill warning">⏳ Pending Approval</span>;
      case 'CANCELLED': return <span className="pill neutral">✕ Cancelled</span>;
      default: return <span className="pill neutral">{status}</span>;
    }
  };

  return (
    <div className="page-content fade-in purchase-orders-page">
      {/* Header */}
      <div className="page-header flex-between">
        <div>
          <span className="eyebrow">Procurement & Receiving</span>
          <h1 className="page-title">Purchase Orders</h1>
          <p className="page-subtitle">
            Track vendor purchase orders, receive incoming stock shipments, and monitor delivery status.
          </p>
        </div>
        <div className="header-actions">
          {canOperate && (
            <button className="btn btn-primary" onClick={() => setCreateModalOpen(true)}>
              ＋ New Purchase Order
            </button>
          )}
          <Link to="/reorders" className="btn btn-secondary">
            ⚡ Reorder System
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

      {/* KPI Cards */}
      <div className="stats-grid premium-stats" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', marginBottom: 24 }}>
        <StatCard
          icon="🚚"
          label="Orders In Transit"
          value={orders.filter(o => o.status === 'ORDERED').length}
          iconBg="rgba(139,92,246,0.18)"
          trendLabel="Awaiting shipment"
        />
        <StatCard
          icon="⏳"
          label="Partially Received"
          value={orders.filter(o => o.status === 'PARTIALLY_RECEIVED').length}
          iconBg="rgba(99,212,255,0.18)"
          trendLabel="Inbound deliveries"
        />
        <StatCard
          icon="✓"
          label="Completed Orders"
          value={orders.filter(o => o.status === 'RECEIVED').length}
          iconBg="rgba(30,201,139,0.18)"
          trendLabel="Fully delivered"
        />
        <StatCard
          icon="💰"
          label="Total Open Value"
          value={`$${orders
            .filter(o => o.status === 'ORDERED' || o.status === 'PARTIALLY_RECEIVED')
            .reduce((sum, o) => sum + parseFloat(o.total_amount || 0), 0)
            .toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`}
          iconBg="rgba(91,124,255,0.18)"
          trendLabel="Committed procurement"
        />
      </div>

      {/* Filters Bar */}
      <div className="card p-6 filter-panel" style={{ marginBottom: 20 }}>
        <div className="filter-row flex-between" style={{ flexWrap: 'wrap', gap: 12 }}>
          <div className="search-wrapper" style={{ flex: 1, minWidth: 260 }}>
            <span className="search-icon">⌕</span>
            <input
              type="text"
              className="search-input"
              placeholder="Search PO number, supplier, product..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => refetchOrders()}>
            ↻ Refresh
          </button>
        </div>

        <div className="stock-tab-row" style={{ marginTop: 16, display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {PO_STATUS_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={`chip-btn ${statusFilter === f.value ? 'active' : ''}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Orders Table */}
      <div className="card inventory-table-card">
        {loadingOrders ? (
          <div className="flex-center loader-box p-8"><div className="spinner spinner-lg" /></div>
        ) : filteredOrders.length === 0 ? (
          <div className="empty-state large p-8">
            <span>📦</span>
            <p>No purchase orders found.</p>
            {canOperate && (
              <button className="btn btn-primary mt-4" onClick={() => setCreateModalOpen(true)}>
                Create First Purchase Order
              </button>
            )}
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>PO Number</th>
                  <th>Supplier</th>
                  <th>Warehouse</th>
                  <th>Items & Progress</th>
                  <th>Total Amount</th>
                  <th>Delivery Date</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.map((order) => {
                  const totalOrdered = order.items.reduce((sum, it) => sum + it.quantity, 0);
                  const totalReceived = order.items.reduce((sum, it) => sum + it.received_quantity, 0);
                  const progressPct = totalOrdered > 0 ? Math.min(100, Math.round((totalReceived / totalOrdered) * 100)) : 0;

                  return (
                    <tr key={order.id}>
                      <td className="mono-cell" style={{ fontWeight: 700, color: '#63d4ff' }}>
                        {order.po_number}
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{order.supplier_name}</div>
                      </td>
                      <td className="muted-cell">{order.warehouse_name}</td>
                      <td>
                        <div style={{ fontSize: '0.85rem' }}>
                          {order.items.length === 1 ? (
                            <span>{order.items[0].product_name} ({totalReceived}/{totalOrdered})</span>
                          ) : (
                            <span>{order.items.length} Products ({totalReceived}/{totalOrdered} units)</span>
                          )}
                        </div>
                        {/* Mini progress bar */}
                        <div style={{ width: '100%', height: 4, background: 'rgba(255,255,255,0.1)', borderRadius: 2, marginTop: 4, overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${progressPct}%`,
                              height: '100%',
                              background: progressPct === 100 ? '#1ec98b' : '#63d4ff',
                              transition: 'width 0.3s ease',
                            }}
                          />
                        </div>
                      </td>
                      <td className="bold-cell">${Number(order.total_amount).toFixed(2)}</td>
                      <td className="muted-cell" style={{ fontSize: '0.85rem' }}>
                        {order.expected_delivery || 'Not specified'}
                      </td>
                      <td>{getStatusBadge(order.status)}</td>
                      <td>
                        <div className="action-group">
                          <button
                            className="btn btn-secondary btn-sm"
                            onClick={() => setDetailsModalData(order)}
                          >
                            Details
                          </button>

                          {(order.status === 'ORDERED' || order.status === 'PARTIALLY_RECEIVED') && canOperate && (
                            <button
                              className="btn btn-primary btn-sm"
                              onClick={() => openReceiveModal(order)}
                            >
                              📥 Receive Stock
                            </button>
                          )}

                          {order.status === 'ORDERED' && canOperate && (
                            <button
                              className="btn btn-danger btn-sm"
                              onClick={() => {
                                if (window.confirm(`Are you sure you want to cancel ${order.po_number}?`)) {
                                  cancelMutation.mutate(order.id);
                                }
                              }}
                            >
                              Cancel
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

      {/* ── RECEIVE STOCK MODAL (SUPPORTS PARTIAL RECEIVING) ────────────────── */}
      {receiveModalData && (
        <div className="modal-overlay fade-in" onClick={() => setReceiveModalData(null)}>
          <div className="modal-box card p-6" style={{ maxWidth: 640 }} onClick={(e) => e.stopPropagation()}>
            <div className="flex-between" style={{ marginBottom: 16 }}>
              <div>
                <h2 className="modal-title" style={{ margin: 0 }}>Receive Stock — {receiveModalData.po_number}</h2>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 4 }}>
                  Supplier: <strong>{receiveModalData.supplier_name}</strong> · Warehouse: <strong>{receiveModalData.warehouse_name}</strong>
                </div>
              </div>
              <button className="btn-close" onClick={() => setReceiveModalData(null)}>×</button>
            </div>

            <form onSubmit={handleReceiveSubmit}>
              <div className="table-wrapper compact-table" style={{ marginBottom: 20 }}>
                <table>
                  <thead>
                    <tr>
                      <th>Product</th>
                      <th>Ordered</th>
                      <th>Received</th>
                      <th>Remaining</th>
                      <th>Incoming Qty</th>
                    </tr>
                  </thead>
                  <tbody>
                    {receiveModalData.items.map((item) => {
                      const remaining = item.quantity - item.received_quantity;
                      return (
                        <tr key={item.product_id}>
                          <td>
                            <strong>{item.product_name}</strong>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'monospace' }}>{item.sku}</div>
                          </td>
                          <td>{item.quantity}</td>
                          <td style={{ color: item.received_quantity > 0 ? '#1ec98b' : 'inherit' }}>{item.received_quantity}</td>
                          <td style={{ fontWeight: 700, color: remaining > 0 ? '#f7b955' : '#1ec98b' }}>
                            {remaining}
                          </td>
                          <td style={{ width: 130 }}>
                            {remaining > 0 ? (
                              <input
                                type="number"
                                min="0"
                                max={remaining}
                                className="form-input"
                                style={{ width: 100, padding: '6px 10px' }}
                                value={receiveInputs[item.product_id] ?? 0}
                                onChange={(e) => {
                                  const val = parseInt(e.target.value, 10) || 0;
                                  setReceiveInputs({
                                    ...receiveInputs,
                                    [item.product_id]: Math.max(0, Math.min(val, remaining)),
                                  });
                                }}
                              />
                            ) : (
                              <span className="pill success" style={{ fontSize: '0.75rem' }}>Complete</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              <div style={{ background: 'var(--panel-soft)', padding: '10px 14px', borderRadius: 'var(--radius-md)', fontSize: '0.85rem', color: 'var(--text-soft)', marginBottom: 20 }}>
                ℹ Entering incoming quantities will directly increment the warehouse inventory and master product stock count, generating an official stock ledger transaction.
              </div>

              <div className="flex-between gap-3">
                <button type="button" className="btn btn-secondary" onClick={() => setReceiveModalData(null)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={receiveMutation.isPending}
                >
                  {receiveMutation.isPending ? 'Processing Stock...' : '✓ Confirm Stock Receipt'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── ORDER DETAILS MODAL ────────────────────────────────────────────── */}
      {detailsModalData && (
        <div className="modal-overlay fade-in" onClick={() => setDetailsModalData(null)}>
          <div className="modal-box card p-6" style={{ maxWidth: 640 }} onClick={(e) => e.stopPropagation()}>
            <div className="flex-between" style={{ marginBottom: 16 }}>
              <div>
                <h2 className="modal-title" style={{ margin: 0 }}>{detailsModalData.po_number}</h2>
                <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginTop: 4 }}>
                  Order Date: {detailsModalData.order_date} · Status: {getStatusBadge(detailsModalData.status)}
                </div>
              </div>
              <button className="btn-close" onClick={() => setDetailsModalData(null)}>×</button>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 20, background: 'var(--panel-soft)', padding: 14, borderRadius: 'var(--radius-md)' }}>
              <div>Supplier: <strong>{detailsModalData.supplier_name}</strong></div>
              <div>Warehouse: <strong>{detailsModalData.warehouse_name}</strong></div>
              <div>Expected Delivery: <strong>{detailsModalData.expected_delivery || 'N/A'}</strong></div>
              <div>Total Order Cost: <strong style={{ color: '#5b7cff' }}>${Number(detailsModalData.total_amount).toFixed(2)}</strong></div>
            </div>

            <h3 style={{ fontSize: '1rem', marginBottom: 10 }}>Order Line Items</h3>
            <div className="table-wrapper compact-table" style={{ marginBottom: 20 }}>
              <table>
                <thead>
                  <tr>
                    <th>Product</th>
                    <th>Unit Cost</th>
                    <th>Ordered</th>
                    <th>Received</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {detailsModalData.items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.product_name} <small style={{ color: 'var(--text-muted)' }}>({item.sku})</small></td>
                      <td>${Number(item.unit_cost).toFixed(2)}</td>
                      <td>{item.quantity}</td>
                      <td style={{ color: item.received_quantity === item.quantity ? '#1ec98b' : '#f7b955' }}>
                        {item.received_quantity}
                      </td>
                      <td>${Number(item.total_cost).toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex-end">
              <button className="btn btn-secondary" onClick={() => setDetailsModalData(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── CREATE DIRECT PURCHASE ORDER MODAL ──────────────────────────────── */}
      {createModalOpen && (
        <div className="modal-overlay fade-in" onClick={() => setCreateModalOpen(false)}>
          <div className="modal-box card p-6" style={{ maxWidth: 680 }} onClick={(e) => e.stopPropagation()}>
            <div className="flex-between" style={{ marginBottom: 16 }}>
              <h2 className="modal-title" style={{ margin: 0 }}>Create Direct Purchase Order</h2>
              <button className="btn-close" onClick={() => setCreateModalOpen(false)}>×</button>
            </div>

            <form onSubmit={(e) => {
              e.preventDefault();
              const validItems = poItems
                .filter((it) => it.product_id && it.quantity > 0)
                .map((it) => ({
                  product_id: parseInt(it.product_id, 10),
                  quantity: parseInt(it.quantity, 10),
                  unit_cost: it.unit_cost ? parseFloat(it.unit_cost) : undefined,
                }));

              if (validItems.length === 0) {
                setErrorMessage('Please select at least one product with quantity > 0');
                return;
              }

              createOrderMutation.mutate({
                supplier_id: parseInt(selectedSupplierId, 10),
                warehouse_id: parseInt(selectedWarehouseId, 10),
                expected_delivery: poExpectedDate || undefined,
                items: validItems,
              });
            }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
                <div className="form-group">
                  <label className="form-label">Supplier *</label>
                  <select
                    className="form-select"
                    value={selectedSupplierId}
                    onChange={(e) => setSelectedSupplierId(e.target.value)}
                    required
                  >
                    <option value="">Select a supplier...</option>
                    {suppliers.map((s) => (
                      <option key={s.id} value={s.id}>{s.name}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label">Destination Warehouse *</label>
                  <select
                    className="form-select"
                    value={selectedWarehouseId}
                    onChange={(e) => setSelectedWarehouseId(e.target.value)}
                    required
                  >
                    {warehouses.map((w) => (
                      <option key={w.id} value={w.id}>{w.name}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="form-group" style={{ marginBottom: 16 }}>
                <label className="form-label">Expected Delivery Date</label>
                <input
                  type="date"
                  className="form-input"
                  value={poExpectedDate}
                  onChange={(e) => setPoExpectedDate(e.target.value)}
                />
              </div>

              <h4 style={{ margin: '16px 0 8px' }}>Line Items</h4>
              {poItems.map((item, idx) => (
                <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr auto', gap: 8, alignItems: 'center', marginBottom: 8 }}>
                  <select
                    className="form-select"
                    value={item.product_id}
                    onChange={(e) => {
                      const updated = [...poItems];
                      const selProd = products.find(p => String(p.id) === e.target.value);
                      updated[idx].product_id = e.target.value;
                      if (selProd?.unit_cost) updated[idx].unit_cost = selProd.unit_cost;
                      setPoItems(updated);
                    }}
                    required
                  >
                    <option value="">Select product...</option>
                    {products.map((p) => (
                      <option key={p.id} value={p.id}>{p.name} ({p.sku})</option>
                    ))}
                  </select>

                  <input
                    type="number"
                    min="1"
                    placeholder="Qty"
                    className="form-input"
                    value={item.quantity}
                    onChange={(e) => {
                      const updated = [...poItems];
                      updated[idx].quantity = e.target.value;
                      setPoItems(updated);
                    }}
                    required
                  />

                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    placeholder="Cost ($)"
                    className="form-input"
                    value={item.unit_cost}
                    onChange={(e) => {
                      const updated = [...poItems];
                      updated[idx].unit_cost = e.target.value;
                      setPoItems(updated);
                    }}
                  />

                  {poItems.length > 1 && (
                    <button
                      type="button"
                      className="btn btn-danger btn-sm"
                      onClick={() => setPoItems(poItems.filter((_, i) => i !== idx))}
                    >
                      ×
                    </button>
                  )}
                </div>
              ))}

              <button
                type="button"
                className="btn btn-secondary btn-sm"
                style={{ marginTop: 6, marginBottom: 20 }}
                onClick={() => setPoItems([...poItems, { product_id: '', quantity: 10, unit_cost: '' }])}
              >
                ＋ Add Line Item
              </button>

              <div className="flex-between gap-3">
                <button type="button" className="btn btn-secondary" onClick={() => setCreateModalOpen(false)}>
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={createOrderMutation.isPending || !selectedSupplierId}
                >
                  {createOrderMutation.isPending ? 'Creating...' : '✓ Issue Purchase Order'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
