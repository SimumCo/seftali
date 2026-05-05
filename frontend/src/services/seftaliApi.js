import api from './api';

// ŞEFTALİ Customer API
export const sfCustomerAPI = {
  getProfile: () => api.get('/seftali/customer/profile'),
  getProducts: () => api.get('/seftali/customer/products'),
  getDraft: () => api.get('/seftali/customer/draft'),
  startWorkingCopy: () => api.post('/seftali/customer/working-copy/start'),
  updateWorkingCopy: (id, items) => api.patch(`/seftali/customer/working-copy/${id}`, items),
  addWorkingCopyItem: (id, data) => api.post(`/seftali/customer/working-copy/${id}/items`, data),
  submitWorkingCopy: (id) => api.post(`/seftali/customer/working-copy/${id}/submit`),
  getPendingDeliveries: () => api.get('/seftali/customer/deliveries/pending'),
  acceptDelivery: (id) => api.post(`/seftali/customer/deliveries/${id}/accept`),
  rejectDelivery: (id, data) => api.post(`/seftali/customer/deliveries/${id}/reject`, data),
  createStockDeclaration: (data) => api.post('/seftali/customer/stock-declarations', data),
  getPendingVariance: () => api.get('/seftali/customer/variance/pending'),
  applyReasonBulk: (data) => api.post('/seftali/customer/variance/apply-reason-bulk', data),
  dismissBulk: (data) => api.post('/seftali/customer/variance/dismiss-bulk', data),
  getDeliveryHistory: () => api.get('/seftali/customer/deliveries/history'),
  getDailyConsumption: (params) => api.get('/seftali/customer/daily-consumption', { params }),
  getConsumptionSummary: () => api.get('/seftali/customer/daily-consumption/summary'),
};

// ŞEFTALİ Sales API
export const sfSalesAPI = {
  getCustomers: () => api.get('/seftali/sales/customers'),
  getCustomersSummary: () => api.get('/seftali/sales/customers/summary'),
  updateCustomer: (id, data) => api.patch(`/seftali/sales/customers/${id}`, data),
  createDelivery: (data) => api.post('/seftali/sales/deliveries', data),
  getDeliveries: (params) => api.get('/seftali/sales/deliveries', { params }),
  getOrders: (params) => api.get('/seftali/sales/orders', { params }),
  approveOrder: (id) => api.post(`/seftali/sales/orders/${id}/approve`),
  requestEdit: (id, data) => api.post(`/seftali/sales/orders/${id}/request-edit`, data),
  getWarehouseDraft: () => api.get('/seftali/sales/warehouse-draft'),
  getSmartDraftV2: () => api.get('/seftali/sales/smart-draft-v2'),
  submitWarehouseDraft: (data) => api.post('/seftali/sales/warehouse-draft/submit', data),
  getCampaigns: () => api.get('/seftali/sales/campaigns'),
  addCampaignToOrder: (data) => api.post('/seftali/sales/campaigns/add-to-order', data),
  getCustomerConsumption: (customerId) => api.get(`/seftali/sales/customers/${customerId}/consumption`),
  // Plasiyer Sipariş Hesaplama
  getRouteOrderCalculation: (routeDay) => api.get(`/seftali/sales/plasiyer/order-calculation`, { params: { route_day: routeDay } }),
  getRouteCustomers: (routeDay) => api.get(`/seftali/sales/plasiyer/route-customers/${routeDay}`),
  getPlasiyerStock: () => api.get('/seftali/sales/plasiyer/stock'),
  updatePlasiyerStock: (data) => api.patch('/seftali/sales/plasiyer/stock', data),
  // Rota Haritası & Optimizasyon
  getRouteMap: (routeDay, optimize = false) => api.get(`/seftali/sales/route-map/${routeDay}`, { params: { optimize } }),
  optimizeRoute: (data) => api.post('/seftali/sales/route-map/optimize', data),
};

// ŞEFTALİ Admin API
export const sfAdminAPI = {
  getHealthSummary: () => api.get('/seftali/admin/health/summary'),
  getVariance: (params) => api.get('/seftali/admin/variance', { params }),
  getDeliveries: (params) => api.get('/seftali/admin/deliveries', { params }),
  getWarehouseOrders: (params) => api.get('/seftali/admin/warehouse-orders', { params }),
  processWarehouseOrder: (id) => api.post(`/seftali/admin/warehouse-orders/${id}/process`),
  // Kampanya yönetimi
  getCampaigns: (params) => api.get('/seftali/admin/campaigns', { params }),
  createCampaign: (data) => api.post('/seftali/admin/campaigns', data),
  updateCampaign: (id, data) => api.patch(`/seftali/admin/campaigns/${id}`, data),
  deleteCampaign: (id) => api.delete(`/seftali/admin/campaigns/${id}`),
  // Sistem Ayarları
  getSettings: () => api.get('/seftali/admin/settings'),
  updateSettings: (data) => api.patch('/seftali/admin/settings', data),
  // Ürün Yönetimi
  getProducts: () => api.get('/seftali/admin/products'),
  getProduct: (id) => api.get(`/seftali/admin/products/${id}`),
  updateProduct: (id, data) => api.patch(`/seftali/admin/products/${id}`, data),
  getDepolar: () => api.get('/seftali/admin/depolar'),
  // Depo Stok Yönetimi
  getWarehouseStock: (params) => api.get('/seftali/admin/warehouse-stock', { params }),
  addWarehouseStock: (data) => api.post('/seftali/admin/warehouse-stock', data),
  updateWarehouseStock: (productId, depoNo, data) => api.patch(`/seftali/admin/warehouse-stock/${productId}?depo_no=${depoNo}`, data),
  bulkUpdateWarehouseStock: (data) => api.post('/seftali/admin/warehouse-stock/bulk', data),
  deleteWarehouseStock: (productId, depoNo) => api.delete(`/seftali/admin/warehouse-stock/${productId}?depo_no=${depoNo}`),
  // Bölge Yönetimi
  getRegions: () => api.get('/seftali/admin/regions'),
  createRegion: (data) => api.post('/seftali/admin/regions', data),
  updateRegion: (id, data) => api.patch(`/seftali/admin/regions/${id}`, data),
  deleteRegion: (id) => api.delete(`/seftali/admin/regions/${id}`),
  seedIstanbulMerkez: () => api.post('/seftali/admin/regions/seed'),
  // Müşteri ve Plasiyer Bölge Atama
  getCustomers: () => api.get('/seftali/admin/customers'),
  updateCustomerRegion: (customerId, regionId) => api.patch(`/seftali/admin/customers/${customerId}/region`, { region_id: regionId }),
  getPlasiyerler: () => api.get('/seftali/admin/users/plasiyerler'),
  updateUserRegion: (userId, regionId) => api.patch(`/seftali/admin/users/${userId}/region`, { region_id: regionId }),
};
