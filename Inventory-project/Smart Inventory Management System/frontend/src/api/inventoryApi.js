import api from './axiosInstance';

export const inventoryApi = {
  // Products
  listProducts: (params) => api.get('/inventory/products', { params }),
  listProductOptions: () => api.get('/inventory/products/options'),
  getProductCounts: () => api.get('/inventory/products/counts'),
  listCategories: () => api.get('/inventory/categories'),
  listSubcategories: (categoryId) => api.get('/inventory/subcategories', {
    params: categoryId ? { category_id: categoryId } : undefined,
  }),
  createCategory: (data) => api.post('/inventory/categories', data),
  deleteCategory: (id) => api.delete(`/inventory/categories/${id}`),
  createSubcategory: (data) => api.post('/inventory/subcategories', data),
  deleteSubcategory: (id) => api.delete(`/inventory/subcategories/${id}`),
  getProduct: (id) => api.get(`/inventory/products/${id}`),
  createProduct: (data) => api.post('/inventory/products', data),
  updateProduct: (id, data) => api.put(`/inventory/products/${id}`, data),
  deleteProduct: (id) => api.delete(`/inventory/products/${id}`),
  adjustStock: (id, delta, reason) =>
    api.patch(`/inventory/products/${id}/stock`, { delta, reason }),
  getLowStock: () => api.get('/inventory/products/low-stock'),
  uploadImage: (file) => {
    const formData = new FormData();
    formData.append('image', file);
    return api.post('/inventory/uploads/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // Reorder Management
  listReorders: (params) => api.get('/inventory/reorders', { params }),
  getRequiredReorders: () => api.get('/inventory/reorders/required'),
  getReorderSummary: () => api.get('/inventory/reorders/summary'),
  getReorder: (id) => api.get(`/inventory/reorders/${id}`),
  createReorder: (data) => api.post('/inventory/reorders', data),
  updateReorder: (id, data) => api.put(`/inventory/reorders/${id}`, data),
  approveReorder: (id) => api.post(`/inventory/reorders/${id}/approve`),
  rejectReorder: (id, rejection_reason) => api.post(`/inventory/reorders/${id}/reject`, { rejection_reason }),
  createPOFromReorder: (id, data) => api.post(`/inventory/reorders/${id}/purchase-order`, data),

  // Suppliers
  listSuppliers: (includeInactive = false) => api.get('/inventory/suppliers', {
    params: includeInactive ? { include_inactive: true } : undefined,
  }),
  getSupplier: (id) => api.get(`/inventory/suppliers/${id}`),
  createSupplier: (data) => api.post('/inventory/suppliers', data),
  updateSupplier: (id, data) => api.put(`/inventory/suppliers/${id}`, data),
  deleteSupplier: (id) => api.delete(`/inventory/suppliers/${id}`),

  // Purchase Orders
  listPurchaseOrders: (params) => api.get('/inventory/purchase-orders', { params }),
  getPurchaseOrder: (id) => api.get(`/inventory/purchase-orders/${id}`),
  createPurchaseOrder: (data) => api.post('/inventory/purchase-orders', data),
  approvePurchaseOrder: (id) => api.post(`/inventory/purchase-orders/${id}/approve`),
  markPurchaseOrderOrdered: (id) => api.post(`/inventory/purchase-orders/${id}/order`),
  receivePurchaseOrder: (id, data) => api.post(`/inventory/purchase-orders/${id}/receive`, data),
  cancelPurchaseOrder: (id) => api.post(`/inventory/purchase-orders/${id}/cancel`),

  // Intelligence & Analytics
  getDashboardSummary: () => api.get('/inventory/analytics/dashboard'),
  getRecentMovements: (limit = 10) => api.get('/inventory/analytics/recent-movements', { params: { limit } }),
  getMovementSummary: (days = 30) => api.get('/inventory/analytics/movements', { params: { days } }),
  getRiskSnapshot: () => api.get('/inventory/analytics/risk'),
  listSeasonalEvents: () => api.get('/inventory/seasonal-events'),
  getSeasonalDemand: (eventId, filters = {}) => api.get('/inventory/seasonal-demand', {
    params: { ...(eventId ? { event_id: eventId } : {}), ...filters },
  }),
  forecastSeasonalProduct: (data) => api.post('/inventory/seasonal-demand/forecast', data),
  createSeasonalEvent: (data) => api.post('/inventory/seasonal-events', data),
  listOffers: () => api.get('/inventory/offers'),
  createOffer: (data) => api.post('/inventory/offers', data),
  updateOffer: (id, data) => api.put(`/inventory/offers/${id}`, data),
  disableOffer: (id) => api.patch(`/inventory/offers/${id}/disable`),
  deleteOffer: (id) => api.delete(`/inventory/offers/${id}`),
  listCampaigns: () => api.get('/inventory/campaigns'),
  createCampaign: (data) => api.post('/inventory/campaigns', data),
  updateCampaign: (id, data) => api.put(`/inventory/campaigns/${id}`, data),
  deleteCampaign: (id) => api.delete(`/inventory/campaigns/${id}`),
  applyCampaignDiscount: (id, data) => api.post(`/inventory/campaigns/${id}/apply-discount`, data),
  listWarehouses: () => api.get('/inventory/warehouses'),
  recordDiscountPerformance: (data) => api.post('/inventory/festive-discounts/performance', data),
  listDiscountPerformance: (festivalEventId) => api.get('/inventory/festive-discounts/performance', {
    params: festivalEventId ? { festival_event_id: festivalEventId } : undefined,
  }),
  // Sales & Point of Sale
  listSalesOrders: (params) => api.get('/inventory/sales', { params }),
  getSalesSummary: () => api.get('/inventory/sales/summary'),
  getSalesOrder: (id) => api.get(`/inventory/sales/${id}`),
  createSalesOrder: (data) => api.post('/inventory/sales', data),
  refundSalesOrder: (id, reason) => api.post(`/inventory/sales/${id}/refund`, { reason }),

  // Notifications & Alerts
  listNotifications: (params) => api.get('/inventory/notifications', { params }),
  getNotificationSummary: () => api.get('/inventory/notifications/summary'),
  markNotificationRead: (id) => api.patch(`/inventory/notifications/${id}/read`),
  markAllNotificationsRead: () => api.post('/inventory/notifications/mark-all-read'),
  scanAlerts: () => api.post('/inventory/notifications/scan-alerts'),

  // Reports & Exports
  getInventoryValuation: () => api.get('/inventory/reports/valuation'),
  getSalesPerformance: (params) => api.get('/inventory/reports/sales-performance', { params }),
  exportInventoryCsv: () => api.get('/inventory/reports/export/inventory-csv', { responseType: 'blob' }),
  exportSalesCsv: (params) => api.get('/inventory/reports/export/sales-csv', { params, responseType: 'blob' }),
  exportMovementsCsv: (limit = 1000) => api.get('/inventory/reports/export/movements-csv', { params: { limit }, responseType: 'blob' }),
};

