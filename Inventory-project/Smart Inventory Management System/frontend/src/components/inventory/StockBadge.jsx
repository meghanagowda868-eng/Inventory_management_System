/**
 * StockBadge — shows colored badge based on product stock status.
 */
export default function StockBadge({ status }) {
  const config = {
    available: { cls: 'badge-success', dot: '●', label: 'Available' },
    low_stock:  { cls: 'badge-warning', dot: '◐', label: 'Low Stock' },
    out_of_stock: { cls: 'badge-danger', dot: '○', label: 'Out of Stock' },
  };

  const { cls, dot, label } = config[status] ?? config.available;

  return (
    <span className={`badge ${cls}`}>
      <span>{dot}</span>
      {label}
    </span>
  );
}
