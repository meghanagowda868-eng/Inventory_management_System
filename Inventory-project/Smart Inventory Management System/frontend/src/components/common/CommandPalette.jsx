import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { inventoryApi } from '../../api/inventoryApi';
import { useAuth } from '../../context/AuthContext';

export default function CommandPalette({ isOpen, onClose }) {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const { user } = useAuth();
  const isManagerOrAdmin = ['admin', 'manager'].includes(user?.role?.toLowerCase());

  // Focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Fetch products for live search
  const { data: products = [] } = useQuery({
    queryKey: ['paletteProducts'],
    queryFn: async () => {
      const res = await inventoryApi.listProducts({ page: 1, limit: 100 });
      return res.data;
    },
    enabled: isOpen,
    staleTime: 60000,
  });

  // Base navigation pages
  const staticItems = [
    { type: 'Page', title: 'Dashboard', path: '/dashboard', icon: '⌂', group: 'Navigation' },
    { type: 'Page', title: 'Sales & POS Checkout', path: '/sales', icon: '🛒', group: 'Navigation' },
    { type: 'Page', title: 'Inventory Stock', path: '/inventory', icon: '▣', group: 'Navigation' },
    { type: 'Page', title: 'Reorder Management', path: '/reorders', icon: '⚡', group: 'Navigation' },
    { type: 'Page', title: 'Purchase Orders', path: '/purchase-orders', icon: '📦', group: 'Navigation' },
    ...(isManagerOrAdmin
      ? [
          { type: 'Page', title: 'Suppliers Directory', path: '/suppliers', icon: '🏢', group: 'Navigation' },
          { type: 'Page', title: 'Reports & Valuation', path: '/reports', icon: '📊', group: 'Navigation' },
          { type: 'Page', title: 'Seasonal Demand', path: '/seasonal-demand', icon: '◒', group: 'Navigation' },
          { type: 'Page', title: 'Campaigns & Deals', path: '/campaigns', icon: '◈', group: 'Navigation' },
          { type: 'Page', title: 'Promotional Offers', path: '/offers', icon: '%', group: 'Navigation' },
        ]
      : []),
    { type: 'Page', title: 'AI Insights & Forecasts', path: '/ai-insights', icon: '✦', group: 'Navigation' },
    { type: 'Page', title: 'My Profile', path: '/profile', icon: '◌', group: 'Navigation' },
  ];

  // Quick Action items
  const actionItems = [
    { type: 'Action', title: 'New Sales Order Checkout', path: '/sales', icon: '＋', group: 'Quick Actions' },
    ...(user?.role === 'admin'
      ? [{ type: 'Action', title: 'Add New Product to Catalog', path: '/inventory/add', icon: '＋', group: 'Quick Actions' }]
      : []),
    { type: 'Action', title: 'Create Reorder Request', path: '/reorders', icon: '⚡', group: 'Quick Actions' },
    ...(isManagerOrAdmin
      ? [{ type: 'Action', title: 'Download Valuation Spreadsheet', path: '/reports', icon: '📥', group: 'Quick Actions' }]
      : []),
  ];

  // Filter products by search query
  const matchingProducts = query.trim()
    ? products
        .filter(
          (p) =>
            p.name.toLowerCase().includes(query.toLowerCase()) ||
            p.sku.toLowerCase().includes(query.toLowerCase()) ||
            (p.category && p.category.toLowerCase().includes(query.toLowerCase()))
        )
        .slice(0, 6)
        .map((p) => ({
          type: 'Product',
          title: p.name,
          subtitle: `SKU: ${p.sku} | In Stock: ${p.quantity} | $${p.price.toFixed(2)}`,
          path: `/inventory/${p.id}`,
          icon: '📦',
          group: 'Inventory Products',
        }))
    : [];

  const filteredStatic = staticItems.filter((item) =>
    item.title.toLowerCase().includes(query.toLowerCase())
  );

  const filteredActions = actionItems.filter((item) =>
    item.title.toLowerCase().includes(query.toLowerCase())
  );

  const allResults = [...matchingProducts, ...filteredActions, ...filteredStatic];

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isOpen) return;

      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev + 1) % Math.max(1, allResults.length));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((prev) => (prev - 1 + allResults.length) % Math.max(1, allResults.length));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (allResults[selectedIndex]) {
          navigate(allResults[selectedIndex].path);
          onClose();
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, selectedIndex, allResults, navigate, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-start justify-center pt-20 p-4 animate-fade-in">
      <div
        className="bg-slate-900/95 border border-indigo-500/30 rounded-2xl w-full max-w-xl shadow-2xl shadow-indigo-950/50 overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4 py-3.5 border-b border-slate-800 bg-slate-850/60">
          <span className="text-slate-400 text-lg mr-3">🔍</span>
          <input
            ref={inputRef}
            type="text"
            placeholder="Search products, pages, quick actions... (or type SKU)"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            className="w-full bg-transparent border-none text-slate-100 placeholder-slate-500 text-sm focus:outline-none"
          />
          <kbd className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-800 border border-slate-700 rounded">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-96 overflow-y-auto p-2 space-y-1">
          {allResults.length === 0 ? (
            <div className="py-10 text-center text-slate-500 text-xs">
              No results found for &ldquo;{query}&rdquo;
            </div>
          ) : (
            allResults.map((item, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={`${item.type}-${item.title}-${idx}`}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  onClick={() => {
                    navigate(item.path);
                    onClose();
                  }}
                  className={`px-3 py-2.5 rounded-xl flex items-center justify-between cursor-pointer transition text-xs ${
                    isSelected
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 shadow-sm'
                      : 'text-slate-300 hover:bg-slate-800/60'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-base p-1.5 rounded-lg bg-slate-800 text-indigo-400">
                      {item.icon}
                    </span>
                    <div className="min-w-0">
                      <div className="font-semibold text-slate-200 truncate">{item.title}</div>
                      {item.subtitle && (
                        <div className="text-[11px] text-slate-400 font-mono truncate">{item.subtitle}</div>
                      )}
                    </div>
                  </div>
                  <span className="text-[10px] uppercase font-bold text-slate-500 px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700/50">
                    {item.group}
                  </span>
                </div>
              );
            })
          )}
        </div>

        {/* Bottom Shortcut Hint Footer */}
        <div className="px-4 py-2 bg-slate-950 border-t border-slate-800/80 flex justify-between items-center text-[11px] text-slate-500">
          <div className="flex gap-3">
            <span>
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-[10px] text-slate-300">↑</kbd>{' '}
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-[10px] text-slate-300">↓</kbd> Navigate
            </span>
            <span>
              <kbd className="px-1.5 py-0.5 bg-slate-800 rounded text-[10px] text-slate-300">↵</kbd> Select
            </span>
          </div>
          <span>Smart Inventory Quick Action</span>
        </div>
      </div>
    </div>
  );
}
