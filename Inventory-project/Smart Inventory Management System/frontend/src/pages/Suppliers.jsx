import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { inventoryApi } from '../api/inventoryApi';
import { useAuth } from '../context/AuthContext';

export default function Suppliers() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const role = user?.role?.toLowerCase();
  const isAdmin = role === 'admin';
  const isManager = role === 'manager';
  const canEdit = isAdmin || isManager;
  const canDelete = isAdmin;

  // View, Search & Filter States
  const [viewMode, setViewMode] = useState('grid'); // 'grid' | 'table'
  const [search, setSearch] = useState('');
  const [filterTab, setFilterTab] = useState('ALL'); // 'ALL' | 'ACTIVE' | 'LOW_STOCK' | 'INACTIVE'
  const [sortBy, setSortBy] = useState('name-asc'); // 'name-asc' | 'name-desc' | 'products-desc' | 'health-desc'

  // Modal & Drawer States
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSupplier, setEditingSupplier] = useState(null);
  const [deletingSupplier, setDeletingSupplier] = useState(null);
  const [selectedSupplier, setSelectedSupplier] = useState(null);
  const [drawerTab, setDrawerTab] = useState('products'); // 'products' | 'orders' | 'details'

  // Quick Reorder Trigger from Supplier Drawer
  const [quickReorderProduct, setQuickReorderProduct] = useState(null);
  const [reorderQty, setReorderQty] = useState(20);
  const [reorderReason, setReorderReason] = useState('Low inventory replenishment');

  // Form State
  const [formData, setFormData] = useState({
    name: '',
    contact_person: '',
    email: '',
    phone: '',
    address: '',
    status: 'ACTIVE',
  });

  const [toastMessage, setToastMessage] = useState(null);

  const showToast = (text, type = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  };

  // ── Queries ───────────────────────────────────────────────────────────────
  const { data: suppliers = [], isLoading: isLoadingSuppliers, refetch: refetchSuppliers } = useQuery({
    queryKey: ['suppliers', true],
    queryFn: () => inventoryApi.listSuppliers(true).then((r) => r.data),
    staleTime: 30000,
  });

  const { data: productsData, isLoading: isLoadingProducts } = useQuery({
    queryKey: ['allProductsCatalog'],
    queryFn: () => inventoryApi.listProducts({ page: 1, limit: 500 }).then((r) => r.data),
    staleTime: 60000,
  });
  const allProducts = productsData?.items || [];

  const { data: purchaseOrders = [] } = useQuery({
    queryKey: ['allPurchaseOrders'],
    queryFn: () => inventoryApi.listPurchaseOrders({ limit: 100 }).then((r) => r.data),
    staleTime: 60000,
  });

  // ── Mutations ─────────────────────────────────────────────────────────────
  const createMutation = useMutation({
    mutationFn: (data) => inventoryApi.createSupplier(data),
    onSuccess: () => {
      showToast('Supplier profile created successfully!');
      setModalOpen(false);
      refetchSuppliers();
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (err) => {
      showToast(err?.response?.data?.detail || err.message || 'Failed to create supplier', 'error');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }) => inventoryApi.updateSupplier(id, data),
    onSuccess: () => {
      showToast('Supplier profile updated successfully!');
      setModalOpen(false);
      setEditingSupplier(null);
      refetchSuppliers();
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (err) => {
      showToast(err?.response?.data?.detail || err.message || 'Failed to update supplier', 'error');
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => inventoryApi.deleteSupplier(id),
    onSuccess: () => {
      showToast('Supplier marked as INACTIVE.');
      setDeletingSupplier(null);
      refetchSuppliers();
      queryClient.invalidateQueries({ queryKey: ['suppliers'] });
    },
    onError: (err) => {
      showToast(err?.response?.data?.detail || err.message || 'Failed to deactivate supplier', 'error');
    },
  });

  const createReorderMutation = useMutation({
    mutationFn: (payload) => inventoryApi.createReorder(payload),
    onSuccess: () => {
      showToast('Reorder request submitted for manager approval!');
      setQuickReorderProduct(null);
      queryClient.invalidateQueries({ queryKey: ['reorders'] });
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
    onError: (err) => {
      showToast(err?.response?.data?.detail || 'Failed to create reorder request', 'error');
    },
  });

  // ── Helper Computations ───────────────────────────────────────────────────
  const supplierStatsMap = useMemo(() => {
    const map = {};
    suppliers.forEach((s) => {
      const prods = allProducts.filter((p) => p.supplier_id === s.id);
      const pos = purchaseOrders.filter((po) => po.supplier_id === s.id);
      const lowStockProds = prods.filter((p) => p.quantity <= p.reorder_point);
      const totalInventoryVal = prods.reduce((sum, p) => sum + (p.price * p.quantity), 0);
      const openPOs = pos.filter((po) => ['DRAFT', 'ORDERED', 'PARTIALLY_RECEIVED'].includes(po.status));
      const inStockPercent = prods.length > 0 ? Math.round(((prods.length - lowStockProds.length) / prods.length) * 100) : 100;

      map[s.id] = {
        products: prods,
        lowStockProducts: lowStockProds,
        purchaseOrders: pos,
        openPOs,
        inventoryValue: totalInventoryVal,
        inStockPercent,
      };
    });
    return map;
  }, [suppliers, allProducts, purchaseOrders]);

  // Filter & Sort Suppliers
  const processedSuppliers = useMemo(() => {
    let list = suppliers.filter((s) => {
      const stats = supplierStatsMap[s.id] || { products: [], lowStockProducts: [] };
      const isActive = s.is_active ?? (s.status === 'ACTIVE');

      if (filterTab === 'ACTIVE' && !isActive) return false;
      if (filterTab === 'INACTIVE' && isActive) return false;
      if (filterTab === 'LOW_STOCK' && stats.lowStockProducts.length === 0) return false;

      if (!search.trim()) return true;
      const q = search.toLowerCase();
      return (
        s.name?.toLowerCase().includes(q) ||
        s.contact_person?.toLowerCase().includes(q) ||
        s.contact_name?.toLowerCase().includes(q) ||
        s.email?.toLowerCase().includes(q) ||
        s.phone?.toLowerCase().includes(q) ||
        s.address?.toLowerCase().includes(q)
      );
    });

    // Sorting
    list.sort((a, b) => {
      if (sortBy === 'name-asc') return (a.name || '').localeCompare(b.name || '');
      if (sortBy === 'name-desc') return (b.name || '').localeCompare(a.name || '');
      if (sortBy === 'products-desc') {
        const countA = supplierStatsMap[a.id]?.products.length || 0;
        const countB = supplierStatsMap[b.id]?.products.length || 0;
        return countB - countA;
      }
      if (sortBy === 'health-desc') {
        const healthA = supplierStatsMap[a.id]?.inStockPercent || 0;
        const healthB = supplierStatsMap[b.id]?.inStockPercent || 0;
        return healthB - healthA;
      }
      return 0;
    });

    return list;
  }, [suppliers, supplierStatsMap, filterTab, search, sortBy]);

  // KPI Metrics
  const activeCount = suppliers.filter((s) => s.is_active).length;
  const linkedProductsCount = allProducts.filter((p) => p.supplier_id).length;
  const totalOpenPOsCount = purchaseOrders.filter((po) => ['DRAFT', 'ORDERED', 'PARTIALLY_RECEIVED'].includes(po.status)).length;
  const lowStockSuppliersCount = suppliers.filter((s) => (supplierStatsMap[s.id]?.lowStockProducts.length || 0) > 0).length;

  const handleCopyContact = (s) => {
    const text = `Supplier: ${s.name}\nContact: ${s.contact_person || s.contact_name || 'N/A'}\nEmail: ${s.email || 'N/A'}\nPhone: ${s.phone || 'N/A'}\nAddress: ${s.address || 'N/A'}`;
    navigator.clipboard.writeText(text);
    showToast(`Copied contact details for ${s.name}!`);
  };

  const handleExportCsv = () => {
    const headers = ['ID', 'Supplier Name', 'Contact Person', 'Email', 'Phone', 'Address', 'Products Linked', 'Status'];
    const rows = suppliers.map((s) => {
      const stats = supplierStatsMap[s.id];
      return [
        s.id,
        `"${s.name || ''}"`,
        `"${s.contact_person || s.contact_name || ''}"`,
        `"${s.email || ''}"`,
        `"${s.phone || ''}"`,
        `"${s.address || ''}"`,
        stats?.products.length || 0,
        s.is_active ? 'ACTIVE' : 'INACTIVE',
      ];
    });
    const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `suppliers_directory_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const openCreateModal = () => {
    setEditingSupplier(null);
    setFormData({
      name: '',
      contact_person: '',
      email: '',
      phone: '',
      address: '',
      status: 'ACTIVE',
    });
    setModalOpen(true);
  };

  const openEditModal = (supplier) => {
    setEditingSupplier(supplier);
    setFormData({
      name: supplier.name || '',
      contact_person: supplier.contact_person || supplier.contact_name || '',
      email: supplier.email || '',
      phone: supplier.phone || '',
      address: supplier.address || '',
      status: supplier.status || (supplier.is_active ? 'ACTIVE' : 'INACTIVE'),
    });
    setModalOpen(true);
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      showToast('Supplier company name is required', 'error');
      return;
    }
    if (editingSupplier) {
      updateMutation.mutate({ id: editingSupplier.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleQuickReorderSubmit = (e) => {
    e.preventDefault();
    if (!quickReorderProduct) return;
    createReorderMutation.mutate({
      product_id: quickReorderProduct.id,
      requested_quantity: Number(reorderQty),
      reorder_reason: reorderReason,
    });
  };

  return (
    <div className="page-container fade-in">
      {/* ── Toast Notification Banner ────────────────────────────── */}
      {toastMessage && (
        <div
          className={`fixed top-6 right-6 z-50 px-4 py-3 rounded-2xl shadow-2xl backdrop-blur-md flex items-center gap-3 text-xs font-semibold border transition-all duration-300 animate-fade-in ${
            toastMessage.type === 'error'
              ? 'bg-rose-950/90 text-rose-200 border-rose-500/40 shadow-rose-950/50'
              : 'bg-emerald-950/90 text-emerald-200 border-emerald-500/40 shadow-emerald-950/50'
          }`}
        >
          <span>{toastMessage.type === 'error' ? '🚨' : '✅'}</span>
          <span>{toastMessage.text}</span>
          <button onClick={() => setToastMessage(null)} className="ml-2 text-slate-400 hover:text-white">✕</button>
        </div>
      )}

      {/* ── Hero & Page Header ──────────────────────────────────────── */}
      <div className="card p-6 mb-6 bg-gradient-to-r from-slate-900/90 via-slate-850/80 to-indigo-950/40 border border-slate-700/60 rounded-3xl shadow-xl flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
              Vendor Ecosystem & Procurement Hub
            </span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-100 flex items-center gap-2.5 tracking-tight">
            <span>🏢</span> Supplier & Vendor Management
          </h1>
          <p className="text-slate-400 text-xs sm:text-sm mt-1 max-w-2xl leading-relaxed">
            Authorized vendor directory, procurement point-of-contacts, product catalog linkages, and automated stock replenishment pipelines.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleExportCsv}
            className="btn btn-secondary text-xs px-3.5 py-2.5 rounded-xl flex items-center gap-2 bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700"
          >
            <span>📥</span> Export Directory (CSV)
          </button>
          {canEdit && (
            <button
              onClick={openCreateModal}
              className="btn btn-primary text-xs font-bold px-4 py-2.5 rounded-xl flex items-center gap-2 shadow-lg shadow-indigo-500/30"
            >
              <span>＋</span> Register New Supplier
            </button>
          )}
        </div>
      </div>

      {/* ── Metric Summary KPI Cards ────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Active Suppliers</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center text-sm">
              🏢
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-emerald-400">{activeCount}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">{suppliers.length - activeCount} archived / inactive</div>
          </div>
        </div>

        <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Catalog Linkage</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center text-sm">
              📦
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-indigo-400">{linkedProductsCount}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">SKUs mapped to vendors</div>
          </div>
        </div>

        <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Open Purchase Orders</span>
            <div className="w-8 h-8 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center text-sm">
              📋
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-cyan-400">{totalOpenPOsCount}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">Orders in fulfillment pipeline</div>
          </div>
        </div>

        <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60 flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 uppercase font-bold tracking-wider">Supply Risk Status</span>
            <div className="w-8 h-8 rounded-xl bg-amber-500/10 text-amber-400 flex items-center justify-center text-sm">
              ⚠️
            </div>
          </div>
          <div className="mt-3">
            <div className="text-3xl font-extrabold text-amber-400">{lowStockSuppliersCount}</div>
            <div className="text-[11px] text-slate-500 mt-0.5">Vendors with low-stock SKUs</div>
          </div>
        </div>
      </div>

      {/* ── Control Bar: Search, Filter Tabs & View Toggle ──────────── */}
      <div className="card p-4 mb-6 bg-slate-800/50 border border-slate-700/50 rounded-2xl flex flex-wrap items-center justify-between gap-4">
        {/* Search Field */}
        <div className="flex-1 min-w-[280px] relative">
          <span className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 text-sm">⌕</span>
          <input
            type="text"
            className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-700 rounded-xl text-slate-100 placeholder-slate-500 text-xs focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition"
            placeholder="Search vendor name, contact person, email, phone, city..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {/* Filter Pills */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-xl bg-slate-900/80 p-1 border border-slate-700/60">
            {[
              { key: 'ALL', label: 'All Suppliers' },
              { key: 'ACTIVE', label: `Active (${activeCount})` },
              { key: 'LOW_STOCK', label: `Low Stock (${lowStockSuppliersCount})` },
              { key: 'INACTIVE', label: 'Archived' },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setFilterTab(tab.key)}
                className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                  filterTab === tab.key
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Sort Selector */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-700 text-slate-200 text-xs focus:outline-none"
          >
            <option value="name-asc">Sort: Name (A to Z)</option>
            <option value="name-desc">Sort: Name (Z to A)</option>
            <option value="products-desc">Sort: Most Products</option>
            <option value="health-desc">Sort: Highest In-Stock %</option>
          </select>

          {/* Grid vs Table Toggle */}
          <div className="flex rounded-xl bg-slate-900/80 p-1 border border-slate-700/60">
            <button
              onClick={() => setViewMode('grid')}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                viewMode === 'grid' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>▦</span> Cards
            </button>
            <button
              onClick={() => setViewMode('table')}
              className={`px-2.5 py-1 rounded-lg text-xs font-semibold transition flex items-center gap-1 ${
                viewMode === 'table' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <span>☰</span> Table
            </button>
          </div>
        </div>
      </div>

      {/* ── Main Suppliers List View ─────────────────────────────────── */}
      {isLoadingSuppliers ? (
        <div className="card p-14 text-center text-slate-400 text-xs flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <span>Syncing supplier directory and catalog mappings...</span>
        </div>
      ) : processedSuppliers.length === 0 ? (
        <div className="card p-12 text-center text-slate-400 border border-dashed border-slate-700 rounded-2xl">
          <div className="text-4xl mb-3">🏢</div>
          <h3 className="text-base font-bold text-slate-200">No Suppliers Found</h3>
          <p className="text-xs text-slate-500 mt-1">
            {search ? `No vendors match "${search}".` : 'Get started by creating your first supplier profile.'}
          </p>
          {canEdit && (
            <button onClick={openCreateModal} className="btn btn-primary text-xs px-4 py-2 mt-4 rounded-xl">
              ＋ Add Supplier Profile
            </button>
          )}
        </div>
      ) : viewMode === 'grid' ? (
        /* ── GRID CARDS VIEW ─────────────────────────────────────── */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {processedSuppliers.map((s) => {
            const stats = supplierStatsMap[s.id] || {
              products: [],
              lowStockProducts: [],
              purchaseOrders: [],
              openPOs: [],
              inStockPercent: 100,
            };
            const initials = (s.name || 'S')
              .split(' ')
              .map((w) => w[0])
              .slice(0, 2)
              .join('')
              .toUpperCase();

            return (
              <div
                key={s.id}
                className="card p-5 bg-slate-800/60 border border-slate-700/60 rounded-2xl flex flex-col justify-between hover:border-indigo-500/40 hover:shadow-2xl transition group relative overflow-hidden"
              >
                {/* Top Subtle Gradient Accent */}
                <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-indigo-500 via-purple-500 to-cyan-400 opacity-60 group-hover:opacity-100 transition" />

                <div>
                  {/* Header Row */}
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-black text-sm shadow-md shadow-indigo-500/20">
                        {initials}
                      </div>
                      <div>
                        <h3
                          onClick={() => setSelectedSupplier(s)}
                          className="font-bold text-slate-100 text-sm group-hover:text-indigo-300 cursor-pointer transition flex items-center gap-1.5"
                        >
                          {s.name}
                        </h3>
                        <div className="text-[11px] text-slate-500 font-mono">Vendor ID #{s.id}</div>
                      </div>
                    </div>

                    <span
                      className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${
                        s.is_active
                          ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                          : 'bg-slate-700/50 text-slate-400 border border-slate-600'
                      }`}
                    >
                      {s.is_active ? 'ACTIVE' : 'INACTIVE'}
                    </span>
                  </div>

                  {/* Supplier Summary Badges */}
                  <div className="grid grid-cols-2 gap-2 my-3 p-2.5 bg-slate-900/60 rounded-xl border border-slate-800">
                    <div>
                      <div className="text-[10px] text-slate-400 uppercase font-semibold">Catalog Items</div>
                      <div className="text-sm font-bold text-slate-200 mt-0.5 flex items-center gap-1.5">
                        <span>{stats.products.length} Products</span>
                        {stats.lowStockProducts.length > 0 && (
                          <span className="text-[10px] font-bold text-rose-400 bg-rose-500/10 px-1.5 py-0.5 rounded border border-rose-500/20">
                            {stats.lowStockProducts.length} low
                          </span>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-[10px] text-slate-400 uppercase font-semibold">Stock Health</div>
                      <div className="text-sm font-bold text-slate-200 mt-0.5 flex items-center gap-1">
                        <span className={stats.inStockPercent < 80 ? 'text-amber-400' : 'text-emerald-400'}>
                          {stats.inStockPercent}%
                        </span>
                        <span className="text-[10px] text-slate-500 font-normal">in stock</span>
                      </div>
                    </div>
                  </div>

                  {/* Contact Info List */}
                  <div className="space-y-2 py-1 text-xs text-slate-300">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500 text-sm">👤</span>
                      <span className="font-medium text-slate-200 truncate">
                        {s.contact_person || s.contact_name || 'No contact assigned'}
                      </span>
                    </div>

                    {s.email && (
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500 text-sm">✉️</span>
                        <a
                          href={`mailto:${s.email}`}
                          className="text-indigo-400 hover:text-indigo-300 hover:underline truncate text-xs"
                        >
                          {s.email}
                        </a>
                      </div>
                    )}

                    {s.phone && (
                      <div className="flex items-center gap-2">
                        <span className="text-slate-500 text-sm">📞</span>
                        <a
                          href={`tel:${s.phone}`}
                          className="text-slate-300 hover:text-indigo-300 font-mono text-xs"
                        >
                          {s.phone}
                        </a>
                      </div>
                    )}

                    {s.address && (
                      <div className="flex items-start gap-2 text-slate-400 text-[11px]">
                        <span className="text-slate-500 text-sm mt-0.5">📍</span>
                        <span className="line-clamp-1">{s.address}</span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Card Bottom Actions */}
                <div className="pt-4 mt-3 border-t border-slate-700/50 flex items-center justify-between gap-2">
                  <button
                    onClick={() => {
                      setSelectedSupplier(s);
                      setDrawerTab('products');
                    }}
                    className="btn btn-secondary text-xs py-1.5 px-3 rounded-xl flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200"
                  >
                    View Catalog
                  </button>

                  <button
                    onClick={() => navigate('/purchase-orders')}
                    className="btn btn-primary text-xs py-1.5 px-3 rounded-xl flex-1 shadow-sm font-semibold"
                  >
                    📦 Issue PO
                  </button>

                  <button
                    onClick={() => handleCopyContact(s)}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition"
                    title="Copy Contact Details"
                  >
                    📋
                  </button>

                  {canEdit && (
                    <button
                      onClick={() => openEditModal(s)}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-indigo-300 transition"
                      title="Edit Profile"
                    >
                      ✎
                    </button>
                  )}

                  {canDelete && s.is_active && (
                    <button
                      onClick={() => setDeletingSupplier(s)}
                      className="p-1.5 rounded-lg bg-slate-800 hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 transition"
                      title="Deactivate Supplier"
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        /* ── TABLE VIEW ─────────────────────────────────────────── */
        <div className="card overflow-hidden bg-slate-800/60 border border-slate-700/60 rounded-2xl shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300">
              <thead className="bg-slate-900/90 uppercase font-bold text-slate-400 border-b border-slate-700">
                <tr>
                  <th className="px-5 py-3.5">Supplier Name</th>
                  <th className="px-4 py-3.5">Contact Person</th>
                  <th className="px-4 py-3.5">Contact Channels</th>
                  <th className="px-4 py-3.5">Location</th>
                  <th className="px-3 py-3.5 text-center">Catalog SKUs</th>
                  <th className="px-3 py-3.5 text-center">Stock Health</th>
                  <th className="px-3 py-3.5 text-center">Status</th>
                  <th className="px-5 py-3.5 text-center">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/40">
                {processedSuppliers.map((s) => {
                  const stats = supplierStatsMap[s.id] || { products: [], inStockPercent: 100 };
                  return (
                    <tr key={s.id} className="hover:bg-slate-700/20 transition">
                      <td className="px-5 py-3.5 font-bold text-slate-100">
                        <div
                          onClick={() => setSelectedSupplier(s)}
                          className="hover:text-indigo-400 cursor-pointer transition font-semibold"
                        >
                          {s.name}
                        </div>
                        <div className="text-[11px] font-mono text-slate-500">ID #{s.id}</div>
                      </td>

                      <td className="px-4 py-3.5 text-slate-300 font-medium">
                        {s.contact_person || s.contact_name || '—'}
                      </td>

                      <td className="px-4 py-3.5">
                        {s.email && (
                          <a href={`mailto:${s.email}`} className="text-indigo-400 hover:underline block truncate text-xs">
                            {s.email}
                          </a>
                        )}
                        {s.phone && <div className="text-slate-400 font-mono text-[11px]">{s.phone}</div>}
                      </td>

                      <td className="px-4 py-3.5 text-slate-400 max-w-[200px] truncate">
                        {s.address || '—'}
                      </td>

                      <td className="px-3 py-3.5 text-center">
                        <button
                          onClick={() => {
                            setSelectedSupplier(s);
                            setDrawerTab('products');
                          }}
                          className="px-2.5 py-1 rounded-full text-[11px] font-bold bg-indigo-500/15 text-indigo-300 hover:bg-indigo-500/25 border border-indigo-500/25"
                        >
                          {stats.products.length} Items
                        </button>
                      </td>

                      <td className="px-3 py-3.5 text-center">
                        <span className={`font-bold ${stats.inStockPercent < 80 ? 'text-amber-400' : 'text-emerald-400'}`}>
                          {stats.inStockPercent}%
                        </span>
                      </td>

                      <td className="px-3 py-3.5 text-center">
                        <span
                          className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${
                            s.is_active
                              ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30'
                              : 'bg-slate-700/50 text-slate-400 border border-slate-600'
                          }`}
                        >
                          {s.is_active ? 'ACTIVE' : 'INACTIVE'}
                        </span>
                      </td>

                      <td className="px-5 py-3.5 text-center">
                        <div className="flex items-center justify-center gap-1.5">
                          <button
                            onClick={() => setSelectedSupplier(s)}
                            className="btn btn-secondary text-xs px-2.5 py-1 rounded-lg"
                          >
                            Details
                          </button>
                          {canEdit && (
                            <button
                              onClick={() => openEditModal(s)}
                              className="btn btn-secondary text-xs px-2.5 py-1 rounded-lg text-indigo-300 hover:text-indigo-200"
                            >
                              Edit
                            </button>
                          )}
                          {canDelete && s.is_active && (
                            <button
                              onClick={() => setDeletingSupplier(s)}
                              className="btn btn-secondary text-xs px-2.5 py-1 rounded-lg text-rose-400 hover:text-rose-300"
                            >
                              Deactivate
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
        </div>
      )}

      {/* ── SUPPLIER DETAILED SLIDE-OVER DRAWER ─────────────────────── */}
      {selectedSupplier && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-end p-0 sm:p-4 animate-fade-in">
          <div
            className="bg-slate-900 border-l sm:border border-slate-700/80 w-full sm:max-w-2xl h-full sm:h-[90vh] sm:rounded-3xl shadow-2xl flex flex-col overflow-hidden"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Drawer Header */}
            <div className="px-6 py-5 border-b border-slate-800 bg-slate-850/80 flex justify-between items-start">
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white font-black text-base shadow-md">
                  {(selectedSupplier.name || 'S').slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <h2 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                    {selectedSupplier.name}
                  </h2>
                  <div className="text-xs text-slate-400 mt-0.5">
                    {selectedSupplier.contact_person || 'Authorized Supplier'} • ID #{selectedSupplier.id}
                  </div>
                </div>
              </div>
              <button
                onClick={() => setSelectedSupplier(null)}
                className="text-slate-400 hover:text-slate-200 text-xl font-bold p-1"
              >
                ✕
              </button>
            </div>

            {/* Drawer Navigation Tabs */}
            <div className="flex border-b border-slate-800 px-6 bg-slate-900">
              {[
                { key: 'products', label: `Catalog (${supplierStatsMap[selectedSupplier.id]?.products.length || 0})`, icon: '📦' },
                { key: 'orders', label: `Purchase Orders (${supplierStatsMap[selectedSupplier.id]?.purchaseOrders.length || 0})`, icon: '📋' },
                { key: 'details', label: 'Company Profile', icon: '🏢' },
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setDrawerTab(tab.key)}
                  className={`py-3 px-4 text-xs font-bold border-b-2 transition flex items-center gap-2 ${
                    drawerTab === tab.key
                      ? 'border-indigo-500 text-indigo-400'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <span>{tab.icon}</span> {tab.label}
                </button>
              ))}
            </div>

            {/* Drawer Body Content */}
            <div className="p-6 overflow-y-auto space-y-4 flex-1">
              {/* TAB 1: PRODUCTS */}
              {drawerTab === 'products' && (
                <div className="space-y-4">
                  <div className="flex justify-between items-center text-xs text-slate-400">
                    <span>Products supplied by {selectedSupplier.name}</span>
                    <button
                      onClick={() => navigate('/purchase-orders')}
                      className="text-indigo-400 hover:text-indigo-300 font-semibold"
                    >
                      ＋ Issue Multi-item PO →
                    </button>
                  </div>

                  {supplierStatsMap[selectedSupplier.id]?.products.length === 0 ? (
                    <div className="text-center py-12 border border-dashed border-slate-700/80 rounded-2xl text-slate-500 text-xs">
                      No products currently linked to this supplier.
                    </div>
                  ) : (
                    <div className="border border-slate-700/80 rounded-2xl overflow-hidden shadow-inner">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="bg-slate-800 text-slate-400 border-b border-slate-700">
                          <tr>
                            <th className="px-4 py-2.5">Product</th>
                            <th className="px-3 py-2.5">SKU</th>
                            <th className="px-3 py-2.5 text-right">Cost</th>
                            <th className="px-3 py-2.5 text-right">Stock</th>
                            <th className="px-3 py-2.5 text-center">Status</th>
                            <th className="px-3 py-2.5 text-center">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 bg-slate-900/60">
                          {supplierStatsMap[selectedSupplier.id]?.products.map((p) => {
                            const isLow = p.quantity <= p.reorder_point;
                            return (
                              <tr key={p.id} className="hover:bg-slate-800/40 transition">
                                <td className="px-4 py-3 font-semibold text-slate-100">{p.name}</td>
                                <td className="px-3 py-3 font-mono text-indigo-400 text-[11px]">{p.sku}</td>
                                <td className="px-3 py-3 text-right text-slate-400">
                                  ${p.unit_cost ? p.unit_cost.toFixed(2) : '0.00'}
                                </td>
                                <td className="px-3 py-3 text-right font-bold text-slate-200">{p.quantity}</td>
                                <td className="px-3 py-3 text-center">
                                  <span
                                    className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                      p.quantity === 0
                                        ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                                        : isLow
                                        ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                        : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                    }`}
                                  >
                                    {p.quantity === 0 ? 'Out of Stock' : isLow ? 'Low Stock' : 'Healthy'}
                                  </span>
                                </td>
                                <td className="px-3 py-3 text-center">
                                  <button
                                    onClick={() => {
                                      setQuickReorderProduct(p);
                                      setReorderQty(p.reorder_quantity || 20);
                                    }}
                                    className="px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-indigo-600/20 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/30 transition"
                                  >
                                    ⚡ Reorder
                                  </button>
                                </td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: PURCHASE ORDERS */}
              {drawerTab === 'orders' && (
                <div className="space-y-4">
                  {supplierStatsMap[selectedSupplier.id]?.purchaseOrders.length === 0 ? (
                    <div className="text-center py-12 border border-dashed border-slate-700/80 rounded-2xl text-slate-500 text-xs">
                      No purchase orders recorded for this supplier yet.
                    </div>
                  ) : (
                    <div className="border border-slate-700/80 rounded-2xl overflow-hidden shadow-inner">
                      <table className="w-full text-left text-xs text-slate-300">
                        <thead className="bg-slate-800 text-slate-400 border-b border-slate-700">
                          <tr>
                            <th className="px-4 py-2.5">PO Number</th>
                            <th className="px-3 py-2.5">Date</th>
                            <th className="px-3 py-2.5 text-right">Items</th>
                            <th className="px-3 py-2.5 text-right">Total</th>
                            <th className="px-3 py-2.5 text-center">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800 bg-slate-900/60">
                          {supplierStatsMap[selectedSupplier.id]?.purchaseOrders.map((po) => (
                            <tr key={po.id} className="hover:bg-slate-800/40 transition">
                              <td className="px-4 py-3 font-mono font-bold text-indigo-400">{po.po_number}</td>
                              <td className="px-3 py-3 text-slate-400 text-[11px]">
                                {new Date(po.created_at).toLocaleDateString()}
                              </td>
                              <td className="px-3 py-3 text-right font-semibold">{po.items?.length || 0}</td>
                              <td className="px-3 py-3 text-right font-bold text-slate-100">
                                ${po.total_amount ? po.total_amount.toFixed(2) : '0.00'}
                              </td>
                              <td className="px-3 py-3 text-center">
                                <span
                                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                                    po.status === 'RECEIVED'
                                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                      : po.status === 'ORDERED'
                                      ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                                      : 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                  }`}
                                >
                                  {po.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: DETAILS */}
              {drawerTab === 'details' && (
                <div className="space-y-4 text-xs">
                  <div className="bg-slate-800/40 p-4 rounded-2xl border border-slate-700/60 space-y-3">
                    <div className="flex justify-between border-b border-slate-700/60 pb-2">
                      <span className="text-slate-400">Supplier Name:</span>
                      <strong className="text-slate-100">{selectedSupplier.name}</strong>
                    </div>
                    <div className="flex justify-between border-b border-slate-700/60 pb-2">
                      <span className="text-slate-400">Contact Person:</span>
                      <strong className="text-slate-100">{selectedSupplier.contact_person || 'Not provided'}</strong>
                    </div>
                    <div className="flex justify-between border-b border-slate-700/60 pb-2">
                      <span className="text-slate-400">Email Address:</span>
                      <strong className="text-indigo-400">{selectedSupplier.email || 'Not provided'}</strong>
                    </div>
                    <div className="flex justify-between border-b border-slate-700/60 pb-2">
                      <span className="text-slate-400">Direct Phone:</span>
                      <strong className="text-slate-100 font-mono">{selectedSupplier.phone || 'Not provided'}</strong>
                    </div>
                    <div className="flex justify-between border-b border-slate-700/60 pb-2">
                      <span className="text-slate-400">Office / Facility Address:</span>
                      <strong className="text-slate-200 text-right max-w-[280px]">{selectedSupplier.address || 'Not provided'}</strong>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Operational Status:</span>
                      <strong className={selectedSupplier.is_active ? 'text-emerald-400' : 'text-slate-400'}>
                        {selectedSupplier.is_active ? 'ACTIVE (Authorized)' : 'INACTIVE (Archived)'}
                      </strong>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Drawer Footer Actions */}
            <div className="px-6 py-4 border-t border-slate-800 bg-slate-850/80 flex justify-between items-center">
              <button
                onClick={() => handleCopyContact(selectedSupplier)}
                className="btn btn-secondary text-xs px-3.5 py-2 rounded-xl flex items-center gap-1.5"
              >
                <span>📋</span> Copy Contact Card
              </button>

              <div className="flex gap-2">
                <button
                  onClick={() => setSelectedSupplier(null)}
                  className="btn btn-secondary text-xs px-4 py-2 rounded-xl"
                >
                  Close
                </button>
                <button
                  onClick={() => {
                    setSelectedSupplier(null);
                    navigate('/purchase-orders');
                  }}
                  className="btn btn-primary text-xs font-bold px-5 py-2 rounded-xl shadow-lg shadow-indigo-500/25"
                >
                  📦 Issue Purchase Order
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── QUICK REORDER MODAL ────────────────────────────────────── */}
      {quickReorderProduct && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <div className="flex justify-between items-center border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <span>⚡</span> Quick Reorder Request
              </h3>
              <button onClick={() => setQuickReorderProduct(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>

            <div className="bg-slate-800/40 p-3.5 rounded-2xl border border-slate-700/60 text-xs space-y-1">
              <div className="font-bold text-slate-100">{quickReorderProduct.name}</div>
              <div className="text-indigo-400 font-mono text-[11px]">SKU: {quickReorderProduct.sku}</div>
              <div className="text-slate-400">Current Stock: <strong className="text-slate-200">{quickReorderProduct.quantity} units</strong></div>
            </div>

            <form onSubmit={handleQuickReorderSubmit} className="space-y-3.5">
              <div>
                <label className="text-xs text-slate-300 font-semibold mb-1 block">Requested Quantity *</label>
                <input
                  type="number"
                  min={1}
                  required
                  value={reorderQty}
                  onChange={(e) => setReorderQty(Math.max(1, parseInt(e.target.value) || 1))}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 text-slate-100 text-xs rounded-xl"
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 font-semibold mb-1 block">Reorder Reason</label>
                <input
                  type="text"
                  value={reorderReason}
                  onChange={(e) => setReorderReason(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-950 border border-slate-700 text-slate-100 text-xs rounded-xl"
                />
              </div>

              <div className="pt-2 flex justify-end gap-2.5">
                <button
                  type="button"
                  onClick={() => setQuickReorderProduct(null)}
                  className="btn btn-secondary text-xs px-4 py-2 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createReorderMutation.isPending}
                  className="btn btn-primary text-xs font-bold px-5 py-2 rounded-xl shadow-lg shadow-indigo-500/30 disabled:opacity-50"
                >
                  {createReorderMutation.isPending ? 'Submitting...' : 'Submit Reorder Request'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── CREATE / EDIT SUPPLIER MODAL ──────────────────────────── */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in">
          <div
            className="bg-slate-900 border border-slate-700/80 rounded-3xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="px-6 py-5 border-b border-slate-800 bg-slate-850/60 flex justify-between items-center">
              <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <span>{editingSupplier ? '✎' : '＋'}</span>
                {editingSupplier ? `Edit Supplier Profile: ${editingSupplier.name}` : 'Register New Supplier Profile'}
              </h2>
              <button
                onClick={() => setModalOpen(false)}
                className="text-slate-400 hover:text-slate-200 text-lg font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleFormSubmit} className="p-6 space-y-4">
              <div>
                <label className="text-xs text-slate-300 font-semibold mb-1 block">Company / Vendor Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Dell Direct Supply LLC"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 text-slate-100 text-xs rounded-xl"
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 font-semibold mb-1 block">Point of Contact Person</label>
                <input
                  type="text"
                  placeholder="e.g. Alice Smith (Senior Procurement Rep)"
                  value={formData.contact_person}
                  onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 text-slate-100 text-xs rounded-xl"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3.5">
                <div>
                  <label className="text-xs text-slate-300 font-semibold mb-1 block">Business Email</label>
                  <input
                    type="email"
                    placeholder="orders@supplier.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 text-slate-100 text-xs rounded-xl"
                  />
                </div>

                <div>
                  <label className="text-xs text-slate-300 font-semibold mb-1 block">Direct Phone</label>
                  <input
                    type="text"
                    placeholder="+1 (555) 019-4400"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 text-slate-100 text-xs rounded-xl"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-300 font-semibold mb-1 block">Facility / Billing Address</label>
                <input
                  type="text"
                  placeholder="e.g. 100 Dell Way, Round Rock, TX 78682"
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 text-slate-100 text-xs rounded-xl"
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 font-semibold mb-1 block">Operational Status</label>
                <select
                  value={formData.status}
                  onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                  className="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-700 text-slate-100 text-xs rounded-xl"
                >
                  <option value="ACTIVE">ACTIVE (Authorized for Purchase Orders)</option>
                  <option value="INACTIVE">INACTIVE (Deactivated / Archived)</option>
                </select>
              </div>

              <div className="pt-4 flex items-center justify-end gap-2.5 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="btn btn-secondary text-xs px-4 py-2.5 rounded-xl"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending || updateMutation.isPending}
                  className="btn btn-primary text-xs font-bold px-6 py-2.5 rounded-xl shadow-lg shadow-indigo-500/25 disabled:opacity-50"
                >
                  {editingSupplier
                    ? updateMutation.isPending ? 'Saving Changes...' : '✓ Save Supplier Profile'
                    : createMutation.isPending ? 'Registering...' : '✓ Create Supplier Profile'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── DEACTIVATE CONFIRMATION MODAL ─────────────────────────── */}
      {deletingSupplier && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4 animate-fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-3xl w-full max-w-md p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-rose-400 flex items-center gap-2">
              <span>⚠</span> Deactivate Supplier Profile?
            </h3>
            <p className="text-xs text-slate-300 leading-relaxed">
              Are you sure you want to deactivate <strong>{deletingSupplier.name}</strong>? It will be marked INACTIVE and excluded from active purchase order vendor pickers.
            </p>
            <div className="flex justify-end gap-2.5 pt-2">
              <button
                onClick={() => setDeletingSupplier(null)}
                className="btn btn-secondary text-xs px-4 py-2 rounded-xl"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate(deletingSupplier.id)}
                disabled={deleteMutation.isPending}
                className="btn btn-error text-xs font-bold px-5 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white disabled:opacity-50"
              >
                {deleteMutation.isPending ? 'Deactivating...' : 'Yes, Deactivate Supplier'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
