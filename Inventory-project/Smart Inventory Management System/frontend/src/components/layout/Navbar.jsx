import { useState, useRef, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuth } from '../../context/AuthContext';
import { inventoryApi } from '../../api/inventoryApi';

const PAGE_TITLES = {
  '/dashboard': 'Dashboard',
  '/inventory': 'Inventory',
  '/inventory/add': 'Add Product',
  '/reorders': 'Reorders Management',
  '/purchase-orders': 'Purchase Orders',
  '/suppliers': 'Supplier Directory',
  '/catalog': 'Categories & Catalog',
  '/sales': 'Sales & Point of Sale (POS)',
  '/reports': 'Reports & Financial Analytics',
  '/seasonal-demand': 'Seasonal Demand & Deals',
  '/campaigns': 'Marketing Campaigns',
  '/offers': 'Promotional Offers',
  '/ai-insights': 'AI Insights & Forecasts',
  '/admin/users': 'User Management',
  '/profile': 'My Profile',
};

export default function Navbar({ isCollapsed, onToggleSidebar, onOpenPalette }) {
  const { user } = useAuth();
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [isNotifOpen, setIsNotifOpen] = useState(false);
  const notifRef = useRef(null);

  const title = PAGE_TITLES[pathname]
    ?? (pathname.includes('/inventory/') ? 'Product Details' : 'Smart Inventory');

  const now = new Date().toLocaleDateString('en-US', {
    weekday: 'long', month: 'short', day: 'numeric',
  });

  // Fetch Notification Summary
  const { data: notifData } = useQuery({
    queryKey: ['notifications'],
    queryFn: async () => {
      const res = await inventoryApi.getNotificationSummary();
      return res.data;
    },
    refetchInterval: 30000,
  });

  // Mark all read mutation
  const markAllReadMutation = useMutation({
    mutationFn: () => inventoryApi.markAllNotificationsRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  // Mark single read mutation
  const markSingleReadMutation = useMutation({
    mutationFn: (id) => inventoryApi.markNotificationRead(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  // Scan alerts mutation
  const scanAlertsMutation = useMutation({
    mutationFn: () => inventoryApi.scanAlerts(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    },
  });

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setIsNotifOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const unreadCount = notifData?.unread_count || 0;
  const recentNotifications = notifData?.recent_notifications || [];

  const handleNotificationClick = (notif) => {
    if (!notif.is_read) {
      markSingleReadMutation.mutate(notif.id);
    }
    if (notif.link_url) {
      navigate(notif.link_url);
    }
    setIsNotifOpen(false);
  };

  const getSeverityIcon = (sev) => {
    switch (sev) {
      case 'CRITICAL':
        return '🚨';
      case 'WARNING':
        return '⚠️';
      case 'SUCCESS':
        return '✅';
      default:
        return 'ℹ️';
    }
  };

  return (
    <header className="topnav">
      <div className="topnav-left">
        <button className="sidebar-toggle inline-toggle" onClick={onToggleSidebar} aria-label="Toggle sidebar">
          {isCollapsed ? '☰' : '☰'}
        </button>
        <div>
          <h1 className="topnav-title">{title}</h1>
          <div className="topnav-date">{now}</div>
        </div>
      </div>

      <div className="topnav-actions">
        <button
          type="button"
          onClick={onOpenPalette}
          className="global-search cursor-pointer hover:border-indigo-500/50 transition flex items-center justify-between"
          aria-label="Global search"
        >
          <div className="flex items-center gap-2">
            <span className="search-icon">⌕</span>
            <span className="text-xs text-slate-400">Quick search or action...</span>
          </div>
          <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-slate-400 bg-slate-800/80 border border-slate-700 rounded shadow-sm">
            ⌘K
          </kbd>
        </button>

        {/* Interactive Notifications Popover */}
        <div className="relative" ref={notifRef}>
          <button
            className="icon-button relative"
            onClick={() => setIsNotifOpen((v) => !v)}
            aria-label="Notifications"
          >
            <span>🔔</span>
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 bg-rose-500 text-white text-[10px] font-bold w-4 h-4 rounded-full flex items-center justify-center animate-pulse">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {isNotifOpen && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl z-50 overflow-hidden">
              <div className="px-4 py-3 bg-slate-800/80 border-b border-slate-700/80 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm text-slate-100">Notifications & Alerts</span>
                  {unreadCount > 0 && (
                    <span className="bg-indigo-500/20 text-indigo-400 text-xs px-2 py-0.5 rounded-full font-semibold">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => scanAlertsMutation.mutate()}
                    disabled={scanAlertsMutation.isPending}
                    title="Scan inventory for low stock alerts"
                    className="text-xs text-indigo-400 hover:text-indigo-300 px-2 py-1 rounded hover:bg-slate-700/50"
                  >
                    Scan
                  </button>
                  {unreadCount > 0 && (
                    <button
                      onClick={() => markAllReadMutation.mutate()}
                      className="text-xs text-slate-400 hover:text-slate-200 px-2 py-1 rounded hover:bg-slate-700/50"
                    >
                      Read all
                    </button>
                  )}
                </div>
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-slate-800">
                {recentNotifications.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500">
                    No active notifications. System is healthy!
                  </div>
                ) : (
                  recentNotifications.map((notif) => (
                    <div
                      key={notif.id}
                      onClick={() => handleNotificationClick(notif)}
                      className={`p-3 text-xs transition cursor-pointer flex gap-3 items-start ${
                        notif.is_read ? 'bg-slate-900 hover:bg-slate-800/50 opacity-70' : 'bg-slate-850 hover:bg-slate-800 font-medium'
                      }`}
                    >
                      <span className="text-sm mt-0.5">{getSeverityIcon(notif.severity)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex justify-between items-baseline gap-2">
                          <strong className="text-slate-200 truncate">{notif.title}</strong>
                          <span className="text-[10px] text-slate-500 whitespace-nowrap">
                            {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                        <p className="text-slate-400 mt-0.5 text-[11px] line-clamp-2">{notif.message}</p>
                      </div>
                      {!notif.is_read && (
                        <span className="w-2 h-2 rounded-full bg-indigo-500 mt-1 flex-shrink-0" />
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        <span className="badge badge-info role-badge" style={{ textTransform: 'capitalize' }}>
          {user?.role}
        </span>

        <div className="user-chip">
          <div className="user-avatar">{user?.name?.[0]?.toUpperCase() ?? 'U'}</div>
          <div className="user-meta">
            <strong>{user?.name || 'User'}</strong>
            <span>{user?.email || 'Inventory user'}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
