import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { inventoryApi } from '../api/inventoryApi';

export default function Reports() {
  const [activeTab, setActiveTab] = useState('valuation'); // 'valuation' | 'sales'
  const [salesDays, setSalesDays] = useState('30');
  const [isExporting, setIsExporting] = useState(false);

  // Fetch Valuation Report
  const { data: valuation, isLoading: isLoadingValuation } = useQuery({
    queryKey: ['inventoryValuation'],
    queryFn: async () => {
      const res = await inventoryApi.getInventoryValuation();
      return res.data;
    },
    enabled: activeTab === 'valuation',
  });

  // Calculate Dates for Sales Performance
  const getDates = (days) => {
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - parseInt(days));
    return {
      start_date: start.toISOString().split('T')[0],
      end_date: end.toISOString().split('T')[0],
    };
  };

  // Fetch Sales Performance Report
  const { data: salesReport, isLoading: isLoadingSales } = useQuery({
    queryKey: ['salesPerformance', salesDays],
    queryFn: async () => {
      const dates = getDates(salesDays);
      const res = await inventoryApi.getSalesPerformance(dates);
      return res.data;
    },
    enabled: activeTab === 'sales',
  });

  // Trigger CSV Download Helper
  const downloadBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(new Blob([blob]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.parentNode.removeChild(link);
  };

  const handleExportInventoryCsv = async () => {
    try {
      setIsExporting(true);
      const res = await inventoryApi.exportInventoryCsv();
      downloadBlob(res.data, `inventory_valuation_${new Date().toISOString().split('T')[0]}.csv`);
    } catch (err) {
      console.error('Failed to export inventory CSV', err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportSalesCsv = async () => {
    try {
      setIsExporting(true);
      const dates = getDates(salesDays);
      const res = await inventoryApi.exportSalesCsv(dates);
      downloadBlob(res.data, `sales_orders_${dates.start_date}_to_${dates.end_date}.csv`);
    } catch (err) {
      console.error('Failed to export sales CSV', err);
    } finally {
      setIsExporting(false);
    }
  };

  const handleExportMovementsCsv = async () => {
    try {
      setIsExporting(true);
      const res = await inventoryApi.exportMovementsCsv(2000);
      downloadBlob(res.data, `stock_ledger_movements_${new Date().toISOString().split('T')[0]}.csv`);
    } catch (err) {
      console.error('Failed to export stock movements CSV', err);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="page-container">
      {/* Header */}
      <div className="page-header flex flex-wrap justify-between items-center gap-4 mb-6">
        <div>
          <h2 className="text-2xl font-bold text-slate-100 flex items-center gap-2">
            <span>📊</span> Reports & Financial Analytics
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Enterprise asset valuation, sales performance KPIs, gross profit metrics, and spreadsheet exports.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={handleExportInventoryCsv}
            disabled={isExporting}
            className="btn btn-secondary text-xs px-3.5 py-2 rounded-lg flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 disabled:opacity-50"
          >
            <span>📥</span> Export Valuation CSV
          </button>
          <button
            onClick={handleExportSalesCsv}
            disabled={isExporting}
            className="btn btn-secondary text-xs px-3.5 py-2 rounded-lg flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 disabled:opacity-50"
          >
            <span>📥</span> Export Sales CSV
          </button>
          <button
            onClick={handleExportMovementsCsv}
            disabled={isExporting}
            className="btn btn-secondary text-xs px-3.5 py-2 rounded-lg flex items-center gap-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 disabled:opacity-50"
          >
            <span>📥</span> Export Ledger CSV
          </button>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex border-b border-slate-700/80 mb-6 gap-2">
        <button
          onClick={() => setActiveTab('valuation')}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition flex items-center gap-2 ${
            activeTab === 'valuation'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>💼</span> Inventory Asset Valuation
        </button>
        <button
          onClick={() => setActiveTab('sales')}
          className={`px-5 py-3 text-sm font-semibold border-b-2 transition flex items-center gap-2 ${
            activeTab === 'sales'
              ? 'border-indigo-500 text-indigo-400'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <span>📈</span> Sales Performance & Revenue
        </button>
      </div>

      {/* TAB 1: INVENTORY ASSET VALUATION */}
      {activeTab === 'valuation' && (
        <div className="space-y-6">
          {/* Summary KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <div className="text-xs text-slate-400 uppercase font-semibold">Total Asset Cost</div>
              <div className="text-2xl font-bold text-amber-400 mt-1">
                ${valuation ? valuation.total_cost_value.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'}
              </div>
              <div className="text-xs text-slate-500 mt-1">Capital invested in stock</div>
            </div>

            <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <div className="text-xs text-slate-400 uppercase font-semibold">Total Retail Value</div>
              <div className="text-2xl font-bold text-indigo-400 mt-1">
                ${valuation ? valuation.total_retail_value.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'}
              </div>
              <div className="text-xs text-slate-500 mt-1">Potential gross sales revenue</div>
            </div>

            <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <div className="text-xs text-slate-400 uppercase font-semibold">Potential Profit</div>
              <div className="text-2xl font-bold text-emerald-400 mt-1">
                ${valuation ? valuation.total_potential_profit.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'}
              </div>
              <div className="text-xs text-slate-500 mt-1">Expected unrealized gain</div>
            </div>

            <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <div className="text-xs text-slate-400 uppercase font-semibold">Overall Margin</div>
              <div className="text-2xl font-bold text-cyan-400 mt-1">
                {valuation ? valuation.overall_margin_percent.toFixed(1) : '0'}%
              </div>
              <div className="text-xs text-slate-500 mt-1">Average portfolio margin</div>
            </div>

            <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <div className="text-xs text-slate-400 uppercase font-semibold">Total Stock Units</div>
              <div className="text-2xl font-bold text-slate-100 mt-1">
                {valuation ? valuation.total_units_in_stock.toLocaleString() : '0'}
              </div>
              <div className="text-xs text-slate-500 mt-1">{valuation?.total_products || 0} unique SKUs</div>
            </div>
          </div>

          {/* Product Valuation Breakdown Table */}
          <div className="card overflow-hidden bg-slate-800/60 border border-slate-700/60 rounded-2xl shadow-xl">
            <div className="px-6 py-4 border-b border-slate-700/70 flex justify-between items-center bg-slate-900/50">
              <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
                <span>📦</span> SKU Valuation & Profitability Breakdown
              </h3>
              <div className="flex gap-2">
                {valuation?.low_stock_product_count > 0 && (
                  <span className="badge badge-warning text-xs px-2.5 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    {valuation.low_stock_product_count} Low Stock
                  </span>
                )}
                {valuation?.out_of_stock_product_count > 0 && (
                  <span className="badge badge-error text-xs px-2.5 py-1 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                    {valuation.out_of_stock_product_count} Out of Stock
                  </span>
                )}
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/80 uppercase font-semibold text-slate-400 border-b border-slate-700">
                  <tr>
                    <th className="px-4 py-3">Product Name / SKU</th>
                    <th className="px-4 py-3">Category</th>
                    <th className="px-3 py-3 text-right">In Stock</th>
                    <th className="px-3 py-3 text-right">Cost</th>
                    <th className="px-3 py-3 text-right">Price</th>
                    <th className="px-3 py-3 text-right">Total Cost</th>
                    <th className="px-3 py-3 text-right">Retail Value</th>
                    <th className="px-3 py-3 text-right">Profit</th>
                    <th className="px-3 py-3 text-right">Margin</th>
                    <th className="px-4 py-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/40">
                  {isLoadingValuation ? (
                    <tr>
                      <td colSpan={10} className="text-center py-8 text-slate-400">
                        Calculating valuation metrics...
                      </td>
                    </tr>
                  ) : valuation?.products?.length === 0 ? (
                    <tr>
                      <td colSpan={10} className="text-center py-8 text-slate-400">
                        No product items found.
                      </td>
                    </tr>
                  ) : (
                    valuation?.products?.map((p) => (
                      <tr key={p.product_id} className="hover:bg-slate-700/20 transition">
                        <td className="px-4 py-3 font-medium text-slate-200">
                          {p.product_name}
                          <div className="text-[11px] font-mono text-indigo-400">{p.sku}</div>
                        </td>
                        <td className="px-4 py-3 text-slate-400">{p.category}</td>
                        <td className="px-3 py-3 text-right font-bold text-slate-100">{p.quantity_on_hand}</td>
                        <td className="px-3 py-3 text-right text-slate-400">${p.unit_cost.toFixed(2)}</td>
                        <td className="px-3 py-3 text-right text-slate-300 font-medium">${p.unit_price.toFixed(2)}</td>
                        <td className="px-3 py-3 text-right text-amber-300">${p.total_cost_value.toFixed(2)}</td>
                        <td className="px-3 py-3 text-right text-indigo-300 font-semibold">${p.total_retail_value.toFixed(2)}</td>
                        <td className="px-3 py-3 text-right text-emerald-400 font-bold">${p.potential_profit.toFixed(2)}</td>
                        <td className="px-3 py-3 text-right text-cyan-400 font-semibold">{p.margin_percent.toFixed(1)}%</td>
                        <td className="px-4 py-3 text-center">
                          <span
                            className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-bold ${
                              p.stock_status === 'HEALTHY'
                                ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                                : p.stock_status === 'LOW_STOCK'
                                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                                : p.stock_status === 'OUT_OF_STOCK'
                                ? 'bg-rose-500/20 text-rose-400 border border-rose-500/30'
                                : 'bg-blue-500/20 text-blue-300 border border-blue-500/30'
                            }`}
                          >
                            {p.stock_status}
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: SALES PERFORMANCE & REVENUE */}
      {activeTab === 'sales' && (
        <div className="space-y-6">
          {/* Timeframe Filter */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-slate-400 uppercase">Analysis Period:</span>
            {['7', '30', '90'].map((days) => (
              <button
                key={days}
                onClick={() => setSalesDays(days)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                  salesDays === days
                    ? 'bg-indigo-600 text-white shadow-md'
                    : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                }`}
              >
                Last {days} Days
              </button>
            ))}
          </div>

          {/* Sales Performance KPIs */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <div className="text-xs text-slate-400 uppercase font-semibold">Period Revenue</div>
              <div className="text-2xl font-bold text-emerald-400 mt-1">
                ${salesReport ? salesReport.total_revenue.toLocaleString('en-US', { minimumFractionDigits: 2 }) : '0.00'}
              </div>
              <div className="text-xs text-slate-500 mt-1">Completed orders in period</div>
            </div>

            <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <div className="text-xs text-slate-400 uppercase font-semibold">Completed Orders</div>
              <div className="text-2xl font-bold text-indigo-400 mt-1">
                {salesReport?.total_orders || 0}
              </div>
              <div className="text-xs text-slate-500 mt-1">Transactions fulfilled</div>
            </div>

            <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <div className="text-xs text-slate-400 uppercase font-semibold">Total Items Sold</div>
              <div className="text-2xl font-bold text-amber-400 mt-1">
                {salesReport?.total_units_sold || 0}
              </div>
              <div className="text-xs text-slate-500 mt-1">Units shipped to customers</div>
            </div>

            <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <div className="text-xs text-slate-400 uppercase font-semibold">Avg Order Value</div>
              <div className="text-2xl font-bold text-cyan-400 mt-1">
                ${salesReport ? salesReport.average_order_value.toFixed(2) : '0.00'}
              </div>
              <div className="text-xs text-slate-500 mt-1">Revenue per cart</div>
            </div>

            <div className="stat-card p-4 rounded-2xl bg-slate-800/60 border border-slate-700/60">
              <div className="text-xs text-slate-400 uppercase font-semibold">Discounts Given</div>
              <div className="text-2xl font-bold text-rose-400 mt-1">
                ${salesReport ? salesReport.total_discount_given.toFixed(2) : '0.00'}
              </div>
              <div className="text-xs text-slate-500 mt-1">Promotional savings</div>
            </div>
          </div>

          {/* Top Selling Products Table */}
          <div className="card overflow-hidden bg-slate-800/60 border border-slate-700/60 rounded-2xl shadow-xl">
            <div className="px-6 py-4 border-b border-slate-700/70 bg-slate-900/50">
              <h3 className="font-bold text-slate-200 text-sm flex items-center gap-2">
                <span>🏆</span> Top 10 Best-Selling Products by Revenue
              </h3>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs text-slate-300">
                <thead className="bg-slate-900/80 uppercase font-semibold text-slate-400 border-b border-slate-700">
                  <tr>
                    <th className="px-4 py-3">Rank</th>
                    <th className="px-4 py-3">Product Name</th>
                    <th className="px-4 py-3">SKU</th>
                    <th className="px-4 py-3 text-right">Units Sold</th>
                    <th className="px-4 py-3 text-right">Total Revenue</th>
                    <th className="px-4 py-3 text-right">Gross Profit</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/40">
                  {isLoadingSales ? (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-slate-400">
                        Loading sales performance...
                      </td>
                    </tr>
                  ) : salesReport?.top_products?.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="text-center py-8 text-slate-400">
                        No sales transactions recorded in this period. Use POS / Checkout to generate sales!
                      </td>
                    </tr>
                  ) : (
                    salesReport?.top_products?.map((tp, idx) => (
                      <tr key={tp.product_id} className="hover:bg-slate-700/20 transition">
                        <td className="px-4 py-3 font-bold text-indigo-400">#{idx + 1}</td>
                        <td className="px-4 py-3 font-semibold text-slate-200">{tp.product_name}</td>
                        <td className="px-4 py-3 font-mono text-slate-400">{tp.sku}</td>
                        <td className="px-4 py-3 text-right font-bold text-amber-400">{tp.units_sold}</td>
                        <td className="px-4 py-3 text-right font-bold text-emerald-400">${tp.total_revenue.toFixed(2)}</td>
                        <td className="px-4 py-3 text-right font-bold text-cyan-400">${tp.gross_profit.toFixed(2)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
