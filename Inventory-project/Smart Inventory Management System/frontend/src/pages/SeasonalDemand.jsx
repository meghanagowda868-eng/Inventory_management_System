import { useEffect, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  ArcElement,
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  Filler,
  Legend,
  LinearScale,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js';
import { Bar, Line } from 'react-chartjs-2';
import { inventoryApi } from '../api/inventoryApi';

ChartJS.register(ArcElement, BarElement, CategoryScale, Filler, Legend, LinearScale, LineElement, PointElement, Tooltip);

const NUMBER_FORMAT = new Intl.NumberFormat('en-US');
const EMPTY_RECOMMENDATIONS = [];
const FORECAST_OPTIONS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8, color: '#627089', padding: 18 } },
    tooltip: { mode: 'index', intersect: false },
  },
  interaction: { mode: 'index', intersect: false },
  scales: {
    x: { grid: { display: false }, ticks: { color: '#748198', maxRotation: 25, minRotation: 0 } },
    y: { beginAtZero: true, grid: { color: '#e8edf5' }, ticks: { color: '#748198', precision: 0 } },
  },
};

const CATEGORY_OPTIONS = {
  indexAxis: 'y',
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false }, tooltip: { intersect: false } },
  scales: {
    x: { beginAtZero: true, grid: { color: '#e8edf5' }, ticks: { color: '#748198', precision: 0 } },
    y: { grid: { display: false }, ticks: { color: '#53617a' } },
  },
};

const moneylessNumber = (value) => NUMBER_FORMAT.format(value ?? 0);
const getYear = (event) => event.start_date.slice(0, 4);
const getElectronicsCategory = (item) => {
  const category = item.category?.trim();
  return !category || category.toLowerCase() === 'electronics'
    ? item.subcategory || 'Other electronics'
    : category;
};

function getStockStatus(item) {
  if (item.status === 'REORDER_REQUIRED') return { label: 'Stock Risk', key: 'risk' };
  if (item.status === 'MONITOR') return { label: 'Monitor', key: 'moderate' };
  if (item.demand_level === 'HIGH') return { label: 'High Demand', key: 'high' };
  return { label: 'Sufficient', key: 'sufficient' };
}

export default function SeasonalDemand() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const canManageInventory = ['admin', 'manager'].includes(user?.role);
  const [festivalId, setFestivalId] = useState('');
  const [draftFestivalId, setDraftFestivalId] = useState('');
  const [draftYear, setDraftYear] = useState('');
  const [draftCategoryId, setDraftCategoryId] = useState('');
  const [draftProductId, setDraftProductId] = useState('');
  const [appliedFilters, setAppliedFilters] = useState({});
  const [orderProduct, setOrderProduct] = useState(null);
  const [orderForm, setOrderForm] = useState({ supplier_id: '', new_supplier_name: '', warehouse_id: '', quantity: '', unit_cost: '', expected_delivery: '' });
  const [discountProductId, setDiscountProductId] = useState('');
  const [discountRange, setDiscountRange] = useState({ minimum_discount: '10', maximum_discount: '25', selected_discount: '15' });
  const [discountCampaignName, setDiscountCampaignName] = useState('');
  const [performanceForm, setPerformanceForm] = useState({ units_sold: '', revenue: '', profit: '', campaign_date: new Date().toISOString().slice(0, 10) });
  const [discountError, setDiscountError] = useState('');
  const [eventForm, setEventForm] = useState({ name: '', start_date: '', end_date: '', description: '', keywords: '' });

  const { data: eventData = [], isLoading: eventsLoading } = useQuery({
    queryKey: ['seasonal-events'],
    queryFn: () => inventoryApi.listSeasonalEvents().then((response) => response.data),
    staleTime: 60000,
  });
  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: () => inventoryApi.listCategories().then((response) => response.data),
    staleTime: 60000,
  });
  const { data: products = [] } = useQuery({
    queryKey: ['product-options'],
    queryFn: () => inventoryApi.listProductOptions().then((response) => response.data),
    staleTime: 60000,
  });
  const { data: warehouses = [] } = useQuery({
    queryKey: ['warehouses'],
    queryFn: () => inventoryApi.listWarehouses().then((response) => response.data),
    enabled: canManageInventory,
    staleTime: 60000,
  });
  const { data: suppliers = [] } = useQuery({
    queryKey: ['suppliers'],
    queryFn: () => inventoryApi.listSuppliers().then((response) => response.data),
    enabled: canManageInventory,
    staleTime: 60000,
  });
  const { data: purchaseOrders = [] } = useQuery({
    queryKey: ['purchase-orders'],
    queryFn: () => inventoryApi.listPurchaseOrders().then((response) => response.data),
    enabled: canManageInventory,
    staleTime: 15000,
  });
  const { data: discountHistory = [] } = useQuery({
    queryKey: ['festive-discount-performance', festivalId],
    queryFn: () => inventoryApi.listDiscountPerformance(festivalId).then((response) => response.data),
    enabled: Boolean(festivalId) && canManageInventory,
    staleTime: 15000,
  });

  const events = eventData.filter((event) => event.is_active);
  const years = [...new Set(events.map(getYear))].sort();
  const eventsForYear = events.filter((event) => getYear(event) === draftYear);

  useEffect(() => {
    if (!events.length || festivalId) return;
    const initialEvent = events.find((event) => ['scheduled', 'active'].includes(event.status)) ?? events[0];
    setFestivalId(String(initialEvent.id));
    setDraftFestivalId(String(initialEvent.id));
    setDraftYear(getYear(initialEvent));
    setAppliedFilters({ year: Number(getYear(initialEvent)) });
  }, [events, festivalId]);

  const { data, isLoading, isFetching, isError, refetch } = useQuery({
    queryKey: ['seasonal-demand', festivalId, appliedFilters],
    queryFn: () => inventoryApi.getSeasonalDemand(festivalId, appliedFilters).then((response) => response.data),
    enabled: Boolean(festivalId),
    staleTime: 30000,
  });

  const selectedEvent = events.find((event) => String(event.id) === festivalId);
  const recommendations = data?.recommendations ?? EMPTY_RECOMMENDATIONS;
  const topProducts = [...recommendations]
    .sort((a, b) => b.expected_demand - a.expected_demand)
    .slice(0, 8);
  const riskProducts = recommendations.filter((item) => item.status === 'REORDER_REQUIRED');
  const priorityProduct = riskProducts[0] ?? topProducts[0];
  const discountProduct = recommendations.find((item) => String(item.product_id) === discountProductId) ?? priorityProduct;

  const recommendationRequest = useMutation({
    mutationFn: (payload) => inventoryApi.recommendFestiveDiscount(payload),
    onSuccess: ({ data: recommendation }) => {
      setDiscountRange((current) => ({ ...current, selected_discount: String(recommendation.recommended_discount) }));
      setDiscountCampaignName(`${recommendation.festival} Electronics - ${recommendation.product_name}`);
      setDiscountError('');
    },
    onError: (error) => setDiscountError(error.response?.data?.detail ?? 'Discount recommendation is unavailable.'),
  });
  const simulationRequest = useMutation({
    mutationFn: (payload) => inventoryApi.simulateFestiveDiscount(payload),
    onError: (error) => setDiscountError(error.response?.data?.detail ?? 'The selected discount could not be simulated.'),
  });
  const applyDiscountRequest = useMutation({
    mutationFn: async () => {
      if (!selectedEvent || !discountProduct) throw new Error('Select a festival and product first.');
      const campaignResponse = await inventoryApi.createCampaign({
        name: discountCampaignName.trim(),
        description: `Manager-confirmed ${discountRange.selected_discount}% ${selectedEvent.name} discount for ${discountProduct.product_name}`,
        starts_at: new Date(`${selectedEvent.start_date}T00:00:00`).toISOString(),
        ends_at: new Date(`${selectedEvent.end_date}T23:59:59`).toISOString(),
        festival_event_id: selectedEvent.id,
        minimum_discount: Number(discountRange.minimum_discount),
        maximum_discount: Number(discountRange.maximum_discount),
        selected_discount: Number(discountRange.selected_discount),
        is_enabled: false,
      });
      return inventoryApi.applyCampaignDiscount(campaignResponse.data.id, {
        selected_discount: Number(discountRange.selected_discount),
        product_ids: [discountProduct.product_id],
        category_ids: [],
        subcategory_ids: [],
      });
    },
    onSuccess: () => {
      setDiscountError('');
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      queryClient.invalidateQueries({ queryKey: ['offers'] });
    },
    onError: (error) => setDiscountError(error.response?.data?.detail ?? error.message ?? 'The campaign discount could not be applied.'),
  });
  const recordPerformanceRequest = useMutation({
    mutationFn: (data) => inventoryApi.recordDiscountPerformance(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['festive-discount-performance', festivalId] });
      setPerformanceForm((current) => ({ ...current, units_sold: '', revenue: '', profit: '' }));
    },
    onError: (error) => setDiscountError(error.response?.data?.detail ?? 'Actual performance could not be recorded.'),
  });
  const createEventRequest = useMutation({
    mutationFn: (payload) => inventoryApi.createSeasonalEvent(payload),
    onSuccess: () => {
      setEventForm({ name: '', start_date: '', end_date: '', description: '', keywords: '' });
      queryClient.invalidateQueries({ queryKey: ['seasonal-events'] });
    },
  });

  const createOrderMutation = useMutation({
    mutationFn: async (form) => {
      let supplierId = Number(form.supplier_id);
      if (!supplierId) {
        const supplierResponse = await inventoryApi.createSupplier({ name: form.new_supplier_name });
        supplierId = supplierResponse.data.id;
      }
      return inventoryApi.createPurchaseOrder({
        supplier_id: supplierId,
        warehouse_id: Number(form.warehouse_id),
        expected_delivery: form.expected_delivery || null,
        items: [{
          product_id: orderProduct.product_id,
          quantity: Number(form.quantity),
          unit_cost: Number(form.unit_cost),
        }],
      });
    },
    onSuccess: () => {
      setOrderProduct(null);
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      queryClient.invalidateQueries({ queryKey: ['seasonal-demand'] });
    },
  });

  const orderActionMutation = useMutation({
    mutationFn: ({ orderId, action }) => inventoryApi[action](orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['purchase-orders'] });
      queryClient.invalidateQueries({ queryKey: ['seasonal-demand'] });
      queryClient.invalidateQueries({ queryKey: ['products'] });
    },
  });
  const categoryDemand = new Map();
  recommendations.forEach((item) => {
    const category = getElectronicsCategory(item);
    categoryDemand.set(category, (categoryDemand.get(category) ?? 0) + item.expected_demand);
  });
  const categoryTotals = [...categoryDemand.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  const forecastPeriods = data?.forecast_periods ?? [];
  const hasHistoricalDemand = forecastPeriods.some((period) => period.historical_demand !== null);
  const timelineSteps = ['Normal', 'Increasing', 'High', 'Very high', 'Peak', 'Cooling'];
  const daysRemaining = data?.days_remaining ?? 0;
  const activeTimelineStep = Math.max(0, Math.min(5, Math.floor((28 - daysRemaining) / 7)));
  const highDemandProduct = recommendations.find((item) => item.demand_level === 'HIGH');
  const sufficientProduct = recommendations.find((item) => item.status === 'STOCK_READY');
  const filteredProducts = products.filter((product) => (
    !draftCategoryId || product.category_id === Number(draftCategoryId)
  ));

  const forecastData = {
    labels: forecastPeriods.map((period) => period.label),
    datasets: [
      {
        label: `${selectedEvent?.name ?? 'Festival'} previous year`,
        data: forecastPeriods.map((period) => period.historical_demand),
        borderColor: '#8794aa',
        backgroundColor: '#8794aa',
        borderDash: [5, 5],
        pointRadius: 3,
        tension: 0.35,
        spanGaps: false,
      },
      {
        label: 'Predicted demand',
        data: forecastPeriods.map((period) => period.predicted_demand),
        borderColor: '#3368d4',
        backgroundColor: 'rgba(51, 104, 212, 0.12)',
        pointBackgroundColor: '#3368d4',
        pointRadius: 4,
        borderWidth: 3,
        tension: 0.35,
        fill: true,
      },
    ],
  };

  const categoryData = {
    labels: categoryTotals.map(([category]) => category),
    datasets: [{
      data: categoryTotals.map(([, value]) => value),
      backgroundColor: '#5b7fe0',
      borderRadius: 4,
      barThickness: 13,
    }],
  };

  const handleAnalyze = (event) => {
    event.preventDefault();
    if (draftFestivalId) {
      setFestivalId(draftFestivalId);
      setAppliedFilters({
        year: Number(draftYear),
        ...(draftCategoryId ? { category_id: Number(draftCategoryId) } : {}),
        ...(draftProductId ? { product_id: Number(draftProductId) } : {}),
      });
    }
  };

  const openOrderForm = (item) => {
    const product = products.find((option) => option.id === item.product_id);
    setOrderProduct(item);
    setOrderForm({
      supplier_id: suppliers[0] ? String(suppliers[0].id) : '',
      new_supplier_name: '',
      warehouse_id: warehouses[0] ? String(warehouses[0].id) : '',
      quantity: String(item.recommended_order_quantity),
      unit_cost: product?.unit_cost ? String(product.unit_cost) : '',
      expected_delivery: '',
    });
  };

  const handleRecommendDiscount = () => {
    if (!discountProduct || !selectedEvent) return;
    recommendationRequest.mutate({
      product_id: discountProduct.product_id,
      festival: selectedEvent.name,
      year: Number(getYear(selectedEvent)),
      minimum_discount: Number(discountRange.minimum_discount),
      maximum_discount: Number(discountRange.maximum_discount),
    });
  };

  const handleSimulateDiscount = () => {
    if (!discountProduct || !selectedEvent) return;
    simulationRequest.mutate({
      product_id: discountProduct.product_id,
      festival: selectedEvent.name,
      year: Number(getYear(selectedEvent)),
      minimum_discount: Number(discountRange.minimum_discount),
      maximum_discount: Number(discountRange.maximum_discount),
      selected_discount: Number(discountRange.selected_discount),
    });
  };

  const handleApplyDiscount = () => {
    if (!discountRange.selected_discount || !discountCampaignName.trim()) return;
    if (!window.confirm(`Apply ${discountRange.selected_discount}% to ${discountProduct?.product_name} through a new ${selectedEvent?.name} campaign?`)) return;
    applyDiscountRequest.mutate();
  };

  const updateOrderField = (field) => (event) => {
    setOrderForm((current) => ({ ...current, [field]: event.target.value }));
  };

  const handleYearChange = (year) => {
    setDraftYear(year);
    const nextEvent = events.find((event) => getYear(event) === year);
    if (nextEvent) setDraftFestivalId(String(nextEvent.id));
  };

  const handleCategoryChange = (categoryId) => {
    setDraftCategoryId(categoryId);
    const selectedProduct = products.find((product) => String(product.id) === draftProductId);
    if (selectedProduct && categoryId && selectedProduct.category_id !== Number(categoryId)) {
      setDraftProductId('');
    }
  };

  const selectCalendarEvent = (event) => {
    setDraftYear(getYear(event));
    setDraftFestivalId(String(event.id));
    setFestivalId(String(event.id));
    setAppliedFilters((filters) => ({ ...filters, year: Number(getYear(event)) }));
  };

  return (
    <div className="seasonal-demand-page">
      <div className="seasonal-demand-inner">
        <header className="seasonal-page-header">
          <div>
            <span className="seasonal-eyebrow">Electronics planning</span>
            <h1>Festive Seasonal Demand</h1>
            <p>Analyze festive demand trends and prepare electronic inventory in advance.</p>
          </div>
          <form className="seasonal-filters" onSubmit={handleAnalyze}>
            <label>
              <span>Festival</span>
              <select value={draftFestivalId} onChange={(event) => setDraftFestivalId(event.target.value)} disabled={!events.length}>
                {eventsForYear.map((event) => <option key={event.id} value={event.id}>{event.name}</option>)}
              </select>
            </label>
            <label>
              <span>Year</span>
              <select value={draftYear} onChange={(event) => handleYearChange(event.target.value)} disabled={!years.length}>
                {years.map((year) => <option key={year} value={year}>{year}</option>)}
              </select>
            </label>
            <label>
              <span>Category</span>
              <select value={draftCategoryId} onChange={(event) => handleCategoryChange(event.target.value)} disabled={!categories.length}>
                <option value="">All categories</option>
                {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
              </select>
            </label>
            <label className="seasonal-product-filter">
              <span>Product</span>
              <select value={draftProductId} onChange={(event) => setDraftProductId(event.target.value)} disabled={!filteredProducts.length}>
                <option value="">All products</option>
                {filteredProducts.map((product) => <option key={product.id} value={product.id}>{product.name} · {product.sku}</option>)}
              </select>
            </label>
            <button className="seasonal-analyze-btn" type="submit" disabled={!draftFestivalId || isFetching}>
              {isFetching ? 'Analyzing...' : 'Analyze'}
            </button>
          </form>
        </header>

        {user?.role === 'admin' && <details className="seasonal-event-admin seasonal-panel">
          <summary>Configure festival calendar</summary>
          <form className="seasonal-event-form" onSubmit={(event) => { event.preventDefault(); createEventRequest.mutate({ ...eventForm, keywords: eventForm.keywords.split(',').map((keyword) => keyword.trim()).filter(Boolean) }); }}>
            <label className="form-label">Festival name<input className="form-input" required value={eventForm.name} onChange={(event) => setEventForm((current) => ({ ...current, name: event.target.value }))} placeholder="Pongal, Onam, Eid, Dussehra..." /></label>
            <label className="form-label">Start date<input className="form-input" required type="date" value={eventForm.start_date} onChange={(event) => setEventForm((current) => ({ ...current, start_date: event.target.value }))} /></label>
            <label className="form-label">End date<input className="form-input" required type="date" value={eventForm.end_date} onChange={(event) => setEventForm((current) => ({ ...current, end_date: event.target.value }))} /></label>
            <label className="form-label">Electronic product keywords<input className="form-input" required value={eventForm.keywords} onChange={(event) => setEventForm((current) => ({ ...current, keywords: event.target.value }))} placeholder="smartphone, laptop, speaker" /></label>
            <label className="form-label seasonal-event-description">Description<input className="form-input" value={eventForm.description} onChange={(event) => setEventForm((current) => ({ ...current, description: event.target.value }))} /></label>
            <button className="seasonal-secondary-btn" type="submit" disabled={createEventRequest.isPending}>{createEventRequest.isPending ? 'Saving...' : 'Add festival'}</button>
            {createEventRequest.isError && <span className="seasonal-form-error">{createEventRequest.error?.response?.data?.detail ?? 'Could not add festival.'}</span>}
          </form>
        </details>}

        {isError && (
          <div className="seasonal-error" role="alert">
            <span>Festival demand data is unavailable.</span>
            <button className="seasonal-secondary-btn" type="button" onClick={() => refetch()}>Retry analysis</button>
          </div>
        )}
        {!eventsLoading && events.length === 0 && (
          <div className="seasonal-empty">No active electronic-festival events are configured yet.</div>
        )}
        {eventsLoading && <div className="seasonal-loading" aria-label="Loading festive demand" />}
        {events.length > 0 && !selectedEvent && <div className="seasonal-loading" aria-label="Loading festival forecast" />}
        {selectedEvent && !data && <div className="seasonal-loading" aria-label="Loading festival forecast" />}

        {selectedEvent && data && (
          <>
            <section className="seasonal-event-banner" aria-label="Upcoming festival overview">
              <div className="seasonal-event-title">
                <span>Upcoming Festival</span>
                <h2>{data.season} {getYear(selectedEvent)}</h2>
                <p>{selectedEvent.status === 'active' ? 'Festival period is underway' : 'Plan stock before demand peaks'}</p>
              </div>
              <div className="seasonal-event-metric">
                <span>Days remaining</span>
                <strong>{data.days_remaining}<small> days</small></strong>
              </div>
              <div className="seasonal-event-metric">
                <span>Expected demand change</span>
                <strong className={data.demand_change_percent > 0 ? 'seasonal-positive' : ''}>
                  {data.demand_change_percent === null ? 'No baseline' : `${data.demand_change_percent > 0 ? '+' : ''}${data.demand_change_percent}%`}
                </strong>
              </div>
              <div className="seasonal-event-metric">
                <span>Products at risk</span>
                <strong>{moneylessNumber(data.products_at_risk)}<small> products</small></strong>
              </div>
            </section>

            {isLoading ? <div className="seasonal-loading" aria-label="Loading forecast" /> : (
              <>
                <section className="seasonal-kpi-grid" aria-label="Demand summary">
                  <article className="seasonal-kpi">
                    <span>Predicted demand</span>
                    <strong>{moneylessNumber(data.predicted_demand)} <small>units</small></strong>
                    <em>{data.demand_change_percent === null ? '90-day baseline unavailable' : `${data.demand_change_percent > 0 ? '+' : ''}${data.demand_change_percent}% vs. baseline`}</em>
                  </article>
                  <article className="seasonal-kpi">
                    <span>Current stock</span>
                    <strong>{moneylessNumber(data.current_stock)} <small>units</small></strong>
                    <em>Across active electronic inventory</em>
                  </article>
                  <article className={`seasonal-kpi ${data.stock_gap > 0 ? 'is-risk' : 'is-covered'}`}>
                    <span>Stock gap</span>
                    <strong>{moneylessNumber(data.stock_gap)} <small>units</small></strong>
                    <em>{data.stock_gap > 0 ? 'Predicted demand exceeds available stock' : 'Current stock covers the model forecast'}</em>
                  </article>
                  <article className="seasonal-kpi">
                    <span>Recommended stock</span>
                    <strong>{moneylessNumber(data.recommended_stock)} <small>units</small></strong>
                    <em>Current stock plus identified gaps</em>
                  </article>
                </section>

                <section className="seasonal-readiness-grid" aria-label="Festival readiness">
                  <article className="seasonal-readiness-card ready"><span>Stock Ready</span><strong>{moneylessNumber(data.products_ready)}</strong><small>Products cover demand plus safety stock</small></article>
                  <article className="seasonal-readiness-card monitor"><span>Monitor</span><strong>{moneylessNumber(data.products_to_monitor)}</strong><small>Demand is covered, safety buffer is short</small></article>
                  <article className="seasonal-readiness-card reorder"><span>Reorder Required</span><strong>{moneylessNumber(data.products_requiring_reorder)}</strong><small>Current stock is below predicted demand</small></article>
                </section>

                <section className="seasonal-content-grid">
                  <article className="seasonal-panel seasonal-forecast-panel">
                    <div className="seasonal-panel-heading">
                      <div><span className="seasonal-eyebrow">Six-week view</span><h2>Festival Demand Forecast</h2></div>
                      <span className="seasonal-data-chip">{isFetching ? 'Refreshing' : 'Live forecast'}</span>
                    </div>
                    {!hasHistoricalDemand && <p className="seasonal-history-note">No prior-year {data.season} transactions are recorded. Historical values are left blank rather than estimated.</p>}
                    <div className="seasonal-chart seasonal-line-chart">
                      <Line data={forecastData} options={FORECAST_OPTIONS} />
                    </div>
                    <p className="seasonal-chart-footnote">Forecast includes the current sales run-rate, trend, category relevance, and a festival-week demand profile.</p>
                  </article>

                  <article className="seasonal-panel seasonal-category-panel">
                    <div className="seasonal-panel-heading">
                      <div><span className="seasonal-eyebrow">Product mix</span><h2>Category Demand Analysis</h2></div>
                    </div>
                    {categoryTotals.length ? (
                      <div className="seasonal-chart seasonal-category-chart"><Bar data={categoryData} options={CATEGORY_OPTIONS} /></div>
                    ) : <p className="seasonal-empty-inline">No category-level sales forecast is available for this festival.</p>}
                  </article>
                </section>

                <section className="seasonal-panel seasonal-timeline-panel">
                  <div className="seasonal-panel-heading">
                    <div><span className="seasonal-eyebrow">Replenishment timing</span><h2>Pre-Festival Demand Timeline</h2></div>
                    <span className="seasonal-timeline-caption">Begin stock review now</span>
                  </div>
                  <div className="seasonal-timeline">
                    {forecastPeriods.map((period, index) => (
                      <div className={`seasonal-timeline-step ${index === activeTimelineStep ? 'is-current' : ''}`} key={period.label}>
                        <span className="seasonal-timeline-dot" />
                        <strong>{period.label}</strong>
                        <span>{timelineSteps[index]}</span>
                        <small>{moneylessNumber(period.predicted_demand)} units</small>
                      </div>
                    ))}
                  </div>
                </section>

                <section className="seasonal-panel seasonal-products-panel">
                  <div className="seasonal-panel-heading">
                    <div><span className="seasonal-eyebrow">Prioritized by forecast volume</span><h2>Top Electronics Expected in Demand</h2></div>
                    <span className="seasonal-count-label">{recommendations.length} forecast products</span>
                  </div>
                  {topProducts.length ? (
                    <div className="seasonal-table-scroll">
                      <table className="seasonal-table">
                        <thead><tr><th>Product</th><th>Category</th><th>Predicted demand</th><th>Current stock</th><th>Safety stock</th><th>Order quantity</th><th>Status</th><th>Action</th></tr></thead>
                        <tbody>{topProducts.map((item) => {
                          const status = getStockStatus(item);
                          return (
                            <tr key={item.product_id}>
                              <td><Link to={`/inventory/${item.product_id}`}>{item.product_name}</Link><small>{item.subcategory || 'Electronics'}</small></td>
                              <td>{getElectronicsCategory(item)}</td>
                              <td className="seasonal-number-cell">{moneylessNumber(item.expected_demand)}</td>
                              <td>{moneylessNumber(item.current_stock)}</td>
                              <td>{moneylessNumber(item.safety_stock)}</td>
                              <td className="seasonal-number-cell">{moneylessNumber(item.recommended_order_quantity)}</td>
                              <td><span className={`seasonal-status-badge ${status.key}`}>{status.label}</span></td>
                              <td>{canManageInventory && item.status === 'REORDER_REQUIRED' && <button className="seasonal-order-btn" type="button" onClick={() => openOrderForm(item)}>Order</button>}</td>
                            </tr>
                          );
                        })}</tbody>
                      </table>
                    </div>
                  ) : <p className="seasonal-empty-inline">The sales history does not currently support a product-level forecast.</p>}
                </section>

                <section className="seasonal-content-grid seasonal-lower-grid">
                  <article className="seasonal-panel">
                    <div className="seasonal-panel-heading">
                      <div><span className="seasonal-eyebrow">Additional inventory</span><h2>Festival Stock Requirements</h2></div>
                      <span className="seasonal-count-label">10% planning buffer</span>
                    </div>
                    {riskProducts.length ? (
                      <div className="seasonal-gap-list">
                        {riskProducts.slice(0, 5).map((item) => (
                          <div className="seasonal-gap-row" key={item.product_id}>
                            <div><Link to={`/inventory/${item.product_id}`}>{item.product_name}</Link><span>{getElectronicsCategory(item)}</span></div>
                            <div><span>Stock {moneylessNumber(item.current_stock)}</span><span>Forecast {moneylessNumber(item.expected_demand)}</span></div>
                            <strong>{moneylessNumber(item.suggested_reorder_quantity)} gap</strong>
                            <b>{moneylessNumber(Math.ceil(item.suggested_reorder_quantity * 1.1))} recommended</b>
                          </div>
                        ))}
                      </div>
                    ) : <p className="seasonal-empty-inline">No product-level stock gaps are predicted for this event.</p>}
                  </article>

                  <article className="seasonal-panel seasonal-ai-panel">
                    <div className="seasonal-ai-heading"><span>AI planning note</span><span className="seasonal-ai-mark">AI</span></div>
                    {priorityProduct ? (
                      <>
                        <h2>{priorityProduct.product_name}</h2>
                        <p>{priorityProduct.reason} Forecast demand is {moneylessNumber(priorityProduct.expected_demand)} units against current stock of {moneylessNumber(priorityProduct.current_stock)}. {priorityProduct.suggested_reorder_quantity > 0 ? `Review an additional ${moneylessNumber(priorityProduct.suggested_reorder_quantity)} units before ${data.season}.` : 'Current inventory covers its forecast.'}</p>
                        <div className="seasonal-ai-actions">
                          <Link className="seasonal-secondary-btn" to={`/inventory/${priorityProduct.product_id}`}>View Details</Link>
                          <Link className="seasonal-primary-btn" to={`/inventory/${priorityProduct.product_id}`}>Apply Recommendation</Link>
                        </div>
                      </>
                    ) : <p className="seasonal-empty-inline">No product-specific recommendation is available for this festival yet.</p>}
                  </article>
                </section>

                <section className="seasonal-content-grid seasonal-calendar-grid">
                  <article className="seasonal-panel">
                    <div className="seasonal-panel-heading"><div><span className="seasonal-eyebrow">Plan ahead</span><h2>Festival Calendar</h2></div></div>
                    <div className="seasonal-calendar-list">
                      {events.slice(0, 6).map((event) => (
                        <button className={`seasonal-calendar-item ${String(event.id) === festivalId ? 'is-selected' : ''}`} key={event.id} onClick={() => selectCalendarEvent(event)}>
                          <span><strong>{event.name}</strong><small>{new Date(`${event.start_date}T00:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</small></span>
                          <span className="seasonal-calendar-level">{String(event.id) === festivalId ? `${moneylessNumber(data.products_at_risk)} at risk` : 'Analyze forecast'}</span>
                        </button>
                      ))}
                    </div>
                  </article>

                  <article className="seasonal-panel">
                    <div className="seasonal-panel-heading"><div><span className="seasonal-eyebrow">Action signals</span><h2>Alerts</h2></div></div>
                    <div className="seasonal-alert-list">
                      {highDemandProduct && <div className="seasonal-alert high"><span /><p><strong>High Demand Alert</strong>{highDemandProduct.product_name} is forecast at {moneylessNumber(highDemandProduct.expected_demand)} units.</p></div>}
                      {riskProducts[0] && <div className="seasonal-alert risk"><span /><p><strong>Stock Risk</strong>{riskProducts[0].product_name} has a forecast gap of {moneylessNumber(riskProducts[0].suggested_reorder_quantity)} units.</p></div>}
                      {sufficientProduct && <div className="seasonal-alert sufficient"><span /><p><strong>Stock Sufficient</strong>{sufficientProduct.product_name} covers its forecast demand.</p></div>}
                      {!highDemandProduct && !riskProducts.length && !sufficientProduct && <p className="seasonal-empty-inline">No alerts can be generated without product-level sales history.</p>}
                    </div>
                  </article>
                </section>

                {canManageInventory && <section className="seasonal-panel seasonal-products-panel">
                  <div className="seasonal-panel-heading"><div><span className="seasonal-eyebrow">Manager confirmed purchasing</span><h2>Purchase Orders</h2></div><span className="seasonal-count-label">{purchaseOrders.length} total</span></div>
                  {purchaseOrders.length ? <div className="seasonal-table-scroll"><table className="seasonal-table"><thead><tr><th>Order</th><th>Supplier</th><th>Delivery to</th><th>Items</th><th>Total</th><th>Status</th><th>Next action</th></tr></thead><tbody>
                    {purchaseOrders.map((order) => <tr key={order.id}><td>PO-{String(order.id).padStart(5, '0')}</td><td>{order.supplier_name}</td><td>{order.warehouse_name}</td><td>{order.items.map((item) => `${item.product_name} × ${item.quantity}`).join(', ')}</td><td>{moneylessNumber(order.total_amount)}</td><td><span className={`seasonal-status-badge ${order.status === 'RECEIVED' ? 'sufficient' : order.status === 'PENDING_APPROVAL' ? 'moderate' : 'risk'}`}>{order.status.replaceAll('_', ' ')}</span></td><td><div className="seasonal-order-actions">
                      {order.status === 'PENDING_APPROVAL' && <button type="button" onClick={() => orderActionMutation.mutate({ orderId: order.id, action: 'approvePurchaseOrder' })}>Approve</button>}
                      {order.status === 'APPROVED' && <button type="button" onClick={() => orderActionMutation.mutate({ orderId: order.id, action: 'markPurchaseOrderOrdered' })}>Mark ordered</button>}
                      {order.status === 'ORDERED' && <button type="button" onClick={() => { if (window.confirm(`Confirm all items on PO-${order.id} were received?`)) orderActionMutation.mutate({ orderId: order.id, action: 'receivePurchaseOrder' }); }}>Receive</button>}
                      {['PENDING_APPROVAL', 'APPROVED', 'ORDERED'].includes(order.status) && <button className="cancel" type="button" onClick={() => { if (window.confirm(`Cancel PO-${order.id}?`)) orderActionMutation.mutate({ orderId: order.id, action: 'cancelPurchaseOrder' }); }}>Cancel</button>}
                    </div></td></tr>)}
                  </tbody></table></div> : <p className="seasonal-empty-inline">No purchase orders yet. Suggested quantities require manager confirmation before an order is created.</p>}
                </section>}

                {canManageInventory && <section className="seasonal-content-grid seasonal-discount-grid">
                  <article className="seasonal-panel seasonal-discount-panel">
                    <div className="seasonal-panel-heading"><div><span className="seasonal-eyebrow">Bounded by manager policy</span><h2>Festive Discount Optimization</h2></div><span className="seasonal-data-chip">Recommendation only</span></div>
                    <div className="seasonal-discount-controls">
                      <label className="form-label">Electronic product<select className="form-select" value={discountProduct?.product_id ?? ''} onChange={(event) => { setDiscountProductId(event.target.value); simulationRequest.reset(); recommendationRequest.reset(); }}><option value="">Select product</option>{topProducts.map((item) => <option key={item.product_id} value={item.product_id}>{item.product_name}</option>)}</select></label>
                      <label className="form-label">Minimum (%)<input className="form-input" type="number" min="0" max="100" step="0.5" value={discountRange.minimum_discount} onChange={(event) => setDiscountRange((current) => ({ ...current, minimum_discount: event.target.value, selected_discount: String(Math.max(Number(event.target.value), Number(current.selected_discount))) }))} /></label>
                      <label className="form-label">Maximum (%)<input className="form-input" type="number" min={discountRange.minimum_discount} max="100" step="0.5" value={discountRange.maximum_discount} onChange={(event) => setDiscountRange((current) => ({ ...current, maximum_discount: event.target.value, selected_discount: String(Math.min(Number(event.target.value), Number(current.selected_discount))) }))} /></label>
                      <button className="seasonal-secondary-btn" type="button" disabled={!discountProduct || recommendationRequest.isPending} onClick={handleRecommendDiscount}>{recommendationRequest.isPending ? 'Analyzing...' : 'Get AI recommendation'}</button>
                    </div>
                    {recommendationRequest.data?.data && <div className="seasonal-discount-result"><div><span>AI recommended</span><strong>{recommendationRequest.data.data.recommended_discount}%</strong></div><p>{recommendationRequest.data.data.reason}</p><small>{recommendationRequest.data.data.historical_festival_units ? `${recommendationRequest.data.data.historical_festival_units} recorded festival units` : 'No tagged historical festival sales; use as a planning scenario.'}{recommendationRequest.data.data.margin_cap === null ? ' Unit cost not recorded, so margin is unavailable.' : ` Margin ceiling ${recommendationRequest.data.data.margin_cap}%.`}</small></div>}
                    <label className="seasonal-discount-slider form-label">Manager selected discount <strong>{discountRange.selected_discount}%</strong><input type="range" min={discountRange.minimum_discount} max={discountRange.maximum_discount} step="0.5" value={discountRange.selected_discount} onChange={(event) => { setDiscountRange((current) => ({ ...current, selected_discount: event.target.value })); simulationRequest.reset(); }} disabled={!discountProduct} /></label>
                    <button className="seasonal-secondary-btn" type="button" onClick={handleSimulateDiscount} disabled={!discountProduct || simulationRequest.isPending}>{simulationRequest.isPending ? 'Simulating...' : 'Simulate this discount'}</button>
                    {simulationRequest.data?.data && <div className="seasonal-simulation-grid">{[['Expected units', simulationRequest.data.data.expected_units_sold], ['Revenue', simulationRequest.data.data.revenue.toLocaleString('en-US', { style: 'currency', currency: 'USD' })], ['Customer savings', simulationRequest.data.data.customer_savings.toLocaleString('en-US', { style: 'currency', currency: 'USD' })], ['Estimated profit', simulationRequest.data.data.profit_available ? simulationRequest.data.data.estimated_profit.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) : 'Cost unavailable'], ['Remaining stock', simulationRequest.data.data.remaining_stock]].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}<p>{simulationRequest.data.data.assumptions}</p></div>}
                    <div className="seasonal-campaign-confirm"><label className="form-label">Campaign name<input className="form-input" value={discountCampaignName} onChange={(event) => setDiscountCampaignName(event.target.value)} placeholder="Festival electronics campaign" /></label><button className="seasonal-primary-btn" type="button" onClick={handleApplyDiscount} disabled={!discountProduct || !discountCampaignName.trim() || applyDiscountRequest.isPending}>{applyDiscountRequest.isPending ? 'Applying...' : 'Confirm and apply discount'}</button></div>
                    {discountError && <p className="seasonal-form-error" role="alert">{discountError}</p>}
                    {applyDiscountRequest.isSuccess && <p className="seasonal-form-success" role="status">Campaign offer created and enabled for this product.</p>}
                  </article>
                  <article className="seasonal-panel seasonal-history-panel">
                    <div className="seasonal-panel-heading"><div><span className="seasonal-eyebrow">Actual recorded outcomes</span><h2>Discount History</h2></div><span className="seasonal-count-label">{discountHistory.length} records</span></div>
                    {discountHistory.length ? <div className="seasonal-table-scroll"><table className="seasonal-table"><thead><tr><th>Festival</th><th>Product</th><th>Discount</th><th>Units</th><th>Revenue</th><th>Profit</th><th>Date</th></tr></thead><tbody>{discountHistory.slice(0, 8).map((item) => <tr key={item.id}><td>{item.festival}</td><td>{item.product_name}</td><td>{item.discount_percent}%</td><td>{moneylessNumber(item.units_sold)}</td><td>{Number(item.revenue).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}</td><td>{item.profit === null ? 'Not recorded' : Number(item.profit).toLocaleString('en-US', { style: 'currency', currency: 'USD' })}</td><td>{item.campaign_date}</td></tr>)}</tbody></table></div> : <p className="seasonal-empty-inline">No actual festive discount outcomes are recorded yet. Simulation results are not saved as sales history.</p>}
                    <form className="seasonal-performance-form" onSubmit={(event) => { event.preventDefault(); recordPerformanceRequest.mutate({ festival_event_id: Number(festivalId), campaign_id: null, product_id: Number(discountProductId || priorityProduct?.product_id), discount_percent: Number(discountRange.selected_discount), units_sold: Number(performanceForm.units_sold), revenue: Number(performanceForm.revenue), profit: performanceForm.profit === '' ? null : Number(performanceForm.profit), campaign_date: performanceForm.campaign_date }); }}>
                      <strong>Record actual results</strong><div className="seasonal-order-fields"><input aria-label="Units sold" className="form-input" type="number" min="0" required placeholder="Units sold" value={performanceForm.units_sold} onChange={(event) => setPerformanceForm((current) => ({ ...current, units_sold: event.target.value }))} /><input aria-label="Revenue" className="form-input" type="number" min="0" step="0.01" required placeholder="Revenue" value={performanceForm.revenue} onChange={(event) => setPerformanceForm((current) => ({ ...current, revenue: event.target.value }))} /></div><div className="seasonal-order-fields"><input aria-label="Profit optional" className="form-input" type="number" min="0" step="0.01" placeholder="Profit (optional)" value={performanceForm.profit} onChange={(event) => setPerformanceForm((current) => ({ ...current, profit: event.target.value }))} /><input aria-label="Campaign date" className="form-input" type="date" required value={performanceForm.campaign_date} onChange={(event) => setPerformanceForm((current) => ({ ...current, campaign_date: event.target.value }))} /></div><button className="seasonal-secondary-btn" type="submit" disabled={!discountProduct || recordPerformanceRequest.isPending}>Record actual results</button>
                    </form>
                  </article>
                </section>}

                <footer className="seasonal-method-note">
                  <strong>Forecast method</strong>
                  <span>{data.calculation}</span>
                </footer>
              </>
            )}
          </>
        )}
      </div>
      {orderProduct && (
        <div className="modal-overlay" onClick={() => setOrderProduct(null)}>
          <section className="modal-box seasonal-order-modal" role="dialog" aria-modal="true" aria-labelledby="seasonal-order-title" onClick={(event) => event.stopPropagation()}>
            <h2 className="modal-title" id="seasonal-order-title">Create purchase order</h2>
            <p className="modal-copy">Confirm the supplier, delivery warehouse, and quantity. Nothing is ordered automatically.</p>
            <div className="seasonal-order-context"><strong>{orderProduct.product_name}</strong><span>Stock {moneylessNumber(orderProduct.current_stock)} · Forecast {moneylessNumber(orderProduct.expected_demand)} · Safety {moneylessNumber(orderProduct.safety_stock)} · Suggested {moneylessNumber(orderProduct.recommended_order_quantity)}</span></div>
            <form className="seasonal-order-form" onSubmit={(event) => { event.preventDefault(); createOrderMutation.mutate(orderForm); }}>
              <label className="form-label">Supplier{suppliers.length ? <select className="form-select" value={orderForm.supplier_id} onChange={updateOrderField('supplier_id')} required><option value="">Select supplier</option>{suppliers.map((supplier) => <option key={supplier.id} value={supplier.id}>{supplier.name}</option>)}</select> : <input className="form-input" value={orderForm.new_supplier_name} onChange={updateOrderField('new_supplier_name')} required placeholder="Supplier name" />}</label>
              {suppliers.length > 0 && <label className="form-label">Or add a new supplier<input className="form-input" value={orderForm.new_supplier_name} onChange={(event) => setOrderForm((current) => ({ ...current, new_supplier_name: event.target.value, supplier_id: event.target.value ? '' : current.supplier_id }))} placeholder="Optional supplier name" /></label>}
              <label className="form-label">Warehouse<select className="form-select" value={orderForm.warehouse_id} onChange={updateOrderField('warehouse_id')} required><option value="">Select warehouse</option>{warehouses.filter((warehouse) => warehouse.status === 'ACTIVE').map((warehouse) => <option key={warehouse.id} value={warehouse.id}>{warehouse.name}</option>)}</select></label>
              <div className="seasonal-order-fields"><label className="form-label">Order quantity<input className="form-input" type="number" min="1" required value={orderForm.quantity} onChange={updateOrderField('quantity')} /></label><label className="form-label">Unit cost<input className="form-input" type="number" min="0.01" step="0.01" required value={orderForm.unit_cost} onChange={updateOrderField('unit_cost')} /></label></div>
              <label className="form-label">Expected delivery<input className="form-input" type="date" value={orderForm.expected_delivery} onChange={updateOrderField('expected_delivery')} /></label>
              {orderForm.quantity && orderForm.unit_cost && <div className="seasonal-order-total">Estimated total <strong>{moneylessNumber(Number(orderForm.quantity) * Number(orderForm.unit_cost))}</strong></div>}
              {createOrderMutation.isError && <p className="seasonal-form-error">{createOrderMutation.error?.response?.data?.detail ?? 'Could not create purchase order.'}</p>}
              {createOrderMutation.isSuccess && <p className="seasonal-form-success">Purchase order submitted for approval.</p>}
              <div className="seasonal-ai-actions"><button className="seasonal-secondary-btn" type="button" onClick={() => setOrderProduct(null)}>Cancel</button><button className="seasonal-primary-btn" type="submit" disabled={createOrderMutation.isPending || (!orderForm.supplier_id && !orderForm.new_supplier_name) || !orderForm.warehouse_id || !orderForm.unit_cost}>{createOrderMutation.isPending ? 'Submitting...' : 'Submit purchase order'}</button></div>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
