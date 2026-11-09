import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

export default function Sidebar({ isCollapsed, onToggle }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const role = user?.role?.toLowerCase();
  const isAdmin = role === 'admin';
  const isManager = role === 'manager';
  const isAdminOrManager = isAdmin || isManager;

  const navGroups = [
    {
      key: 'operations',
      title: 'Operations',
      items: [
        { to: '/dashboard', icon: '⌂', label: 'Dashboard' },
        { to: '/sales', icon: '🛒', label: 'Sales & POS' },
        { to: '/inventory', icon: '▣', label: 'Inventory' },
        { to: '/reorders', icon: '⚡', label: 'Reorders' },
        { to: '/purchase-orders', icon: '📦', label: 'Purchase Orders' },
        ...(isAdminOrManager ? [{ to: '/suppliers', icon: '🏢', label: 'Suppliers' }] : []),
        ...(isAdmin ? [{ to: '/inventory/add', icon: '＋', label: 'Add Product' }] : []),
        ...(isAdminOrManager ? [{ to: '/catalog', icon: '⌘', label: 'Categories' }] : []),
      ],
    },
    {
      key: 'intelligence',
      title: 'Intelligence & Deals',
      items: [
        ...(isAdminOrManager ? [{ to: '/reports', icon: '📊', label: 'Reports & Exports' }] : []),
        { to: '/ai-insights', icon: '✦', label: 'AI Insights' },
        ...(isAdminOrManager
          ? [
              { to: '/seasonal-demand', icon: '◒', label: 'Seasonal Demand' },
              { to: '/campaigns', icon: '◈', label: 'Campaigns' },
              { to: '/offers', icon: '%', label: 'Offers' },
            ]
          : []),
      ],
    },
    {
      key: 'system',
      title: 'Settings',
      items: [
        ...(isAdmin ? [{ to: '/admin/users', icon: '👥', label: 'User Management' }] : []),
        { to: '/profile', icon: '◌', label: 'Profile' },
      ],
    },
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <aside className={`sidebar ${isCollapsed ? 'sidebar-collapsed' : ''}`}>
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">S</div>
          {!isCollapsed && (
            <div>
              <div className="sidebar-logo-text">SmartInv</div>
              <div className="sidebar-logo-sub">Inventory Intelligence</div>
            </div>
          )}
        </div>
        <button className="sidebar-toggle" onClick={onToggle} aria-label="Toggle sidebar">
          {isCollapsed ? '›' : '‹'}
        </button>
      </div>

      <nav className="sidebar-nav">
        {navGroups.map((group) => (
          <div key={group.key} className="sidebar-group">
            {!isCollapsed && <div className="sidebar-section-label">{group.title}</div>}
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}
                title={isCollapsed ? item.label : ''}
              >
                <span className="nav-link-icon">{item.icon}</span>
                {!isCollapsed && <span>{item.label}</span>}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-profile">
        <div className="profile-pill">
          <div className="profile-avatar">{user?.name?.[0]?.toUpperCase() ?? 'U'}</div>
          {!isCollapsed && (
            <div className="profile-meta">
              <div className="profile-name">{user?.name || 'User'}</div>
              <div className="profile-role">{user?.role || 'user'}</div>
            </div>
          )}
        </div>
        <button onClick={handleLogout} className="nav-link nav-link-logout" style={{ width: '100%' }}>
          <span className="nav-link-icon">⎋</span>
          {!isCollapsed && <span>Logout</span>}
        </button>
      </div>
    </aside>
  );
}
