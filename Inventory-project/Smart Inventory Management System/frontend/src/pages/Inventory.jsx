import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { inventoryApi } from '../api/inventoryApi';
import StockBadge from '../components/inventory/StockBadge';
import { useAuth } from '../context/AuthContext';

const STOCK_FILTERS = [
  { value: '', label: 'All Products' },
  { value: 'available', label: 'Available' },
  { value: 'low_stock', label: 'Low Stock' },
  { value: 'out_of_stock', label: 'Out of Stock' },
];

export default function Inventory() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const qc = useQueryClient();

  const [search, setSearch] = useState('');
  const [stockFilter, setStockFilter] = useState(searchParams.get('stock_status') || '');
  const [subcategoryId, setSubcategoryId] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [page, setPage] = useState(1);
  const [deleteId, setDeleteId] = useState(null);

  const queryKey = ['products', { page, search, stockFilter, subcategoryId }];

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => inventoryApi.listCategories().then((response) => response.data),
  });
  const { data: subcategories = [] } = useQuery({
    queryKey: ['subcategories'],
    queryFn: () => inventoryApi.listSubcategories().then((response) => response.data),
  });

  const { data, isLoading } = useQuery({
    queryKey,
    queryFn: () =>
      inventoryApi.listProducts({
        page,
        page_size: 20,
        search: search || undefined,
        stock_status: stockFilter || undefined,
        subcategory_id: subcategoryId || undefined,
      }).then(r => r.data),
    placeholderData: (prev) => prev,
    staleTime: 15000,
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => inventoryApi.deleteProduct(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['products'] });
      setDeleteId(null);
    },
  });

  const canDelete = user?.role === 'admin';
  const canCreate = user?.role === 'admin';
  const canEdit = ['admin', 'manager'].includes(user?.role);
  const workspaceLabel = user?.role === 'admin'
    ? 'Admin Workspace'
    : user?.role === 'manager'
      ? 'Manager Workspace'
      : 'Operations View';

  const products = useMemo(() => {
    const items = [...(data?.items ?? [])];
    items.sort((a, b) => {
      if (sortBy === 'price') return Number(b.price) - Number(a.price);
      if (sortBy === 'quantity') return Number(b.quantity) - Number(a.quantity);
      if (sortBy === 'stock_status') return a.stock_status.localeCompare(b.stock_status);
      return a.name.localeCompare(b.name);
    });
    return items;
  }, [data, sortBy]);

  const totalPages = data?.total_pages ?? 1;
  const total = data?.total ?? 0;
  const categoryNames = Object.fromEntries(categories.map((category) => [category.id, category.name]));

  return (
    <div className="page-content fade-in">
      <div className="page-header inventory-header">
        <div>
          <h1 className="page-title">{workspaceLabel}</h1>
          <p className="page-subtitle">
            {user?.role === 'admin'
              ? 'Full control over catalog, inventory, and system product lifecycle.'
              : user?.role === 'manager'
                ? 'Daily inventory operations, stock updates, and operational monitoring.'
                : 'Read-only inventory view.'}
          </p>
        </div>
        {canCreate && (
          <Link to="/inventory/add" className="btn btn-primary">
            ＋ Add Product
          </Link>
        )}
      </div>

      <div className="card p-6 filter-panel">
        <div className="filter-row">
          <div className="search-wrapper">
            <span className="search-icon">⌕</span>
            <input
              id="product-search"
              type="text"
              className="search-input"
              placeholder="Search name, SKU, category..."
              value={search}
              onChange={(e) => {
                setSearch(e.target.value);
                setPage(1);
              }}
            />
          </div>

          <div className="filter-select-wrap">
            <label htmlFor="sort-products" className="sr-only">Sort products</label>
            <select id="sort-products" className="form-select" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
              <option value="name">Sort by name</option>
              <option value="price">Sort by price</option>
              <option value="quantity">Sort by quantity</option>
              <option value="stock_status">Sort by status</option>
            </select>
          </div>

          <div className="filter-select-wrap">
            <label htmlFor="filter-subcategory" className="sr-only">Filter by subcategory</label>
            <select
              id="filter-subcategory"
              className="form-select"
              value={subcategoryId}
              onChange={(event) => { setSubcategoryId(event.target.value); setPage(1); }}
            >
              <option value="">All subcategories</option>
              {subcategories.map((subcategory) => (
                <option key={subcategory.id} value={subcategory.id}>
                  {categoryNames[subcategory.category_id] || 'Unassigned'} / {subcategory.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="stock-tab-row">
          {STOCK_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => { setStockFilter(f.value); setPage(1); }}
              className={`chip-btn ${stockFilter === f.value ? 'active' : ''}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <div className="card inventory-table-card">
        {isLoading ? (
          <div className="flex-center loader-box">
            <div className="spinner spinner-lg" />
          </div>
        ) : products.length === 0 ? (
          <div className="empty-state large">
            <span>📦</span>
            <p>No products found</p>
            {canCreate && <Link to="/inventory/add" className="btn btn-primary">Add first product</Link>}
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Product</th>
                  <th>SKU</th>
                  <th>Category</th>
                  <th>Price</th>
                  <th>Quantity</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {products.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <Link to={`/inventory/${p.id}`} className="link-strong">
                        {p.name}
                      </Link>
                    </td>
                    <td className="mono-cell">{p.sku}</td>
                    <td className="muted-cell">
                      <div>{p.category_name || p.category || '—'}</div>
                      {p.subcategory_name && <small className="table-subcategory">{p.subcategory_name}</small>}
                    </td>
                    <td className="bold-cell">${Number(p.price).toFixed(2)}</td>
                    <td>
                      <span className={`qty-value ${p.stock_status}`}>
                        {p.quantity}
                      </span>
                      <span className="qty-min">/ min {p.minimum_stock}</span>
                    </td>
                    <td><StockBadge status={p.stock_status} /></td>
                    <td>
                      <div className="action-group">
                        <Link to={`/inventory/${p.id}`} className="btn btn-secondary btn-sm">View</Link>
                        {canEdit && <Link to={`/inventory/${p.id}/edit`} className="btn btn-secondary btn-sm">Edit</Link>}
                        {canDelete && <button onClick={() => setDeleteId(p.id)} className="btn btn-danger btn-sm">Delete</button>}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex-between p-6 pagination-bar">
            <span className="page-info">Page {page} of {totalPages}</span>
            <div className="pagination">
              <button className="page-btn" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>‹</button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pageNumber = Math.max(1, Math.min(page - 2, totalPages - 4)) + i;
                return (
                  <button
                    key={pageNumber}
                    className={`page-btn ${pageNumber === page ? 'active' : ''}`}
                    onClick={() => setPage(pageNumber)}
                  >
                    {pageNumber}
                  </button>
                );
              })}
              <button className="page-btn" disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}>›</button>
            </div>
          </div>
        )}
      </div>

      {deleteId && (
        <div className="modal-overlay" onClick={() => setDeleteId(null)}>
          <div className="modal-box" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">Delete product?</h2>
            <p className="modal-copy">This will soft-delete the product and remove it from active inventory views.</p>
            <div className="flex-center gap-3">
              <button className="btn btn-secondary" onClick={() => setDeleteId(null)}>Cancel</button>
              <button className="btn btn-danger" disabled={deleteMutation.isPending} onClick={() => deleteMutation.mutate(deleteId)}>
                {deleteMutation.isPending ? 'Deleting...' : 'Yes, delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
