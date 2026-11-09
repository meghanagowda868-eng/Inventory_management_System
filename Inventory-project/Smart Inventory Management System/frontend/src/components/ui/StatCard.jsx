export function StatCard({ icon, label, value, iconBg, trend, trendLabel }) {
  return (
    <div className="stat-card fade-in">
      <div className="stat-icon" style={{ background: iconBg || 'rgba(99,102,241,0.15)' }}>
        {icon}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="stat-value">{value}</div>
        <div className="stat-label">{label}</div>
        {trend !== undefined && (
          <div className={`stat-trend ${trend >= 0 ? 'text-success' : 'text-danger'}`}>
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}% {trendLabel}
          </div>
        )}
      </div>
    </div>
  );
}
