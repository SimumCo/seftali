// Plasiyer Dashboard - Ana Bileşen
// Alt bileşenler modüler yapıda organize edilmiştir

import React, { useState, useEffect, useCallback } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { sfSalesAPI } from '../services/seftaliApi';
import { useAuth } from '../context/AuthContext';
import { toast } from 'sonner';
import { 
  Truck, ShoppingBag, Plus, Package, LogOut, Users, 
  TrendingUp, Home, Search, Filter, AlertTriangle, 
  BarChart3, RotateCcw, Navigation, ChevronRight,
  Box, Tag, PlugZap
} from 'lucide-react';

// Import Layout Components
import { 
  DashboardLayout, PageHeader, StatCard, EmptyState, Loading, 
  gradients, Badge
} from '../components/ui/DesignSystem';

// Import Plasiyer Page Components
import RutPage from '../components/plasiyer/RutPage';
import WarehouseDraftPage from '../components/plasiyer/WarehouseDraftPage';
import CustomerCard, { CustomerDetailModal } from '../components/plasiyer/CustomerCard';
import OrdersPage from '../components/plasiyer/OrdersPage';
import CreateDeliveryForm from '../components/plasiyer/CreateDeliveryForm';
import StockPage from '../components/plasiyer/StockPage';
import CampaignsPage from '../components/plasiyer/CampaignsPage';
import { DraftCustomersManager } from '../components/plasiyer/DraftCustomersManager';
import GibConnectionPage from './GibConnectionPage';

// Day translations
const dayTranslations = {
  MON: 'Pazartesi', TUE: 'Sali', WED: 'Carsamba',
  THU: 'Persembe', FRI: 'Cuma', SAT: 'Cumartesi', SUN: 'Pazar'
};

// Get today's day code
const getTodayDayCode = () => {
  const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  return days[new Date().getDay()];
};

const PlasiyerDashboardShell = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState(location.pathname === '/plasiyer/gib-connection' ? 'gib-connection' : 'dashboard');
  const [customers, setCustomers] = useState([]);
  const [customersSummary, setCustomersSummary] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [orders, setOrders] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  // Modal state
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  // Stats
  const [stats, setStats] = useState({
    totalCustomers: 0,
    totalSales: 135250,
    pendingOrders: 0,
    suggestedOrders: 0,
    returnRequests: 2
  });

  // Fetch main data
  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [custRes, custSummaryRes, dlvRes, ordRes] = await Promise.all([
        sfSalesAPI.getCustomers(),
        sfSalesAPI.getCustomersSummary(),
        sfSalesAPI.getDeliveries({}),
        sfSalesAPI.getOrders({}),
      ]);
      setCustomers(custRes.data?.data || []);
      setCustomersSummary(custSummaryRes.data?.data || []);
      setDeliveries(dlvRes.data?.data || []);
      setOrders(ordRes.data?.data || []);

      const pendingCount = (ordRes.data?.data || []).filter(o => o.status === 'submitted').length;
      setStats(prev => ({
        ...prev,
        pendingOrders: pendingCount,
        suggestedOrders: (custRes.data?.data || []).length,
        totalCustomers: (custRes.data?.data || []).length,
      }));
    } catch {
      toast.error('Veri yuklenemedi');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch products
  useEffect(() => {
    const loadProducts = async () => {
      try {
        const API_BASE = process.env.REACT_APP_BACKEND_URL;
        const token = localStorage.getItem('token');
        const resp = await fetch(`${API_BASE}/api/seftali/sales/products`, {
          headers: { Authorization: `Bearer ${token}` }
        });
        if (resp.ok) {
          const data = await resp.json();
          setProducts(data?.data || []);
        }
      } catch (error) {
        console.error('Sales products fetch failed:', error);
        toast.error('Ürünler yüklenemedi');
      }
    };

    loadProducts();
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (location.pathname === '/plasiyer/gib-connection') {
      setActiveTab('gib-connection');
    }
  }, [location.pathname]);

  const handleTabChange = (tabId) => {
    setActiveTab(tabId);
    if (tabId === 'gib-connection') {
      navigate('/plasiyer/gib-connection');
      return;
    }
    if (location.pathname === '/plasiyer/gib-connection') {
      navigate('/');
    }
  };

  // Handlers
  const handleCreateDelivery = async (deliveryData) => {
    if (!deliveryData.customer_id) { 
      toast.error('Musteri secin'); 
      return; 
    }
    if (deliveryData.items.length === 0) { 
      toast.error('En az bir urun ekleyin'); 
      return; 
    }

    setSubmitting(true);
    try {
      await sfSalesAPI.createDelivery(deliveryData);
      toast.success('Teslimat olusturuldu');
      setActiveTab('deliveries');
      await fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Teslimat olusturulamadi');
    } finally {
      setSubmitting(false);
    }
  };

  const handleApproveOrder = async (orderId) => {
    try {
      await sfSalesAPI.approveOrder(orderId);
      toast.success('Siparis onaylandi');
      await fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Onay hatasi');
    }
  };

  const handleRequestEdit = async (orderId) => {
    try {
      await sfSalesAPI.requestEdit(orderId, { note: 'Duzenleme gerekli' });
      toast.success('Duzenleme istegi gonderildi');
      await fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Hata');
    }
  };

  // Customer modal handlers
  const handleViewCustomerDetail = (customer) => {
    setSelectedCustomer(customer);
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setSelectedCustomer(null);
  };

  const handleSaveCustomer = async (customerId, formData) => {
    try {
      // Backend'e güncelleme isteği gönder
      await sfSalesAPI.updateCustomer(customerId, formData);
      toast.success('Müşteri bilgileri güncellendi');
      // Veriyi yeniden çek
      await fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Güncelleme başarısız');
      throw err; // Modal'daki hata işleme için throw et
    }
  };

  const handleCallCustomer = (customer) => {
    if (customer.phone) {
      window.open(`tel:${customer.phone}`, '_self');
    } else {
      toast.warning('Telefon numarası bulunamadı');
    }
  };

  const handleMessageCustomer = (customer) => {
    if (customer.phone) {
      window.open(`https://wa.me/${customer.phone.replace(/\D/g, '')}`, '_blank');
    } else {
      toast.warning('Telefon numarası bulunamadı');
    }
  };

  // Filter today's route customers
  const todayCode = getTodayDayCode();
  const todayCustomers = customersSummary.filter(c => {
    const routeDays = c.route_plan?.days || [];
    return routeDays.includes(todayCode);
  });

  // Filter customers by search
  const filteredCustomers = customersSummary.filter(c => 
    !search || c.name?.toLowerCase().includes(search.toLowerCase())
  );

  // Sidebar navigation items
  const sidebarItems = [
    { id: 'dashboard', label: 'Ana Sayfa', icon: Home },
    { id: 'akilli-siparis', label: 'Smart Orders', icon: Package },
    { id: 'customers', label: 'Musteriler', icon: Users },
    { id: 'orders', label: 'Siparisler', icon: ShoppingBag, badge: stats.pendingOrders },
    { id: 'stock', label: 'Stok', icon: Box },
    { id: 'deliveries', label: 'Teslimatlar', icon: Truck },
    { id: 'campaigns', label: 'Kampanyalar', icon: Tag },
    { id: 'gib-connection', label: 'GİB Bağlantı', icon: PlugZap },
  ];

  // Render content based on active tab
  const renderContent = () => {
    if (loading) return <Loading />;

    switch (activeTab) {
      case 'customers':
        return (
          <CustomersPage 
            customers={filteredCustomers} 
            search={search} 
            setSearch={setSearch}
            deliveries={deliveries}
            orders={orders}
            onViewDetail={handleViewCustomerDetail}
            onCall={handleCallCustomer}
            onMessage={handleMessageCustomer}
            salespersonId={user?.id}
          />
        );
      case 'rut':
        return <RutPage routeDay={todayCode} todayCustomers={todayCustomers} />;
      case 'akilli-siparis':
        return <WarehouseDraftPage />;
      case 'orders':
        return <OrdersPage orders={orders} onApprove={handleApproveOrder} onRequestEdit={handleRequestEdit} />;
      case 'deliveries':
        return <DeliveriesPage deliveries={deliveries} />;
      case 'create':
        return <CreateDeliveryForm customers={customers} products={products} onSubmit={handleCreateDelivery} submitting={submitting} />;
      case 'stock':
        return <StockPage products={products} />;
      case 'campaigns':
        return <CampaignsPage />;
      case 'gib-connection':
        return <GibConnectionPage />;
      case 'analytics':
        return <AnalyticsPage />;
      case 'returns':
        return <ReturnsPage />;
      default:
        return (
          <DashboardPage 
            stats={stats} 
            customers={filteredCustomers} 
            search={search} 
            setSearch={setSearch}
            deliveries={deliveries}
            orders={orders}
            onViewDetail={handleViewCustomerDetail}
            onCall={handleCallCustomer}
            onMessage={handleMessageCustomer}
          />
        );
    }
  };

  return (
    <DashboardLayout
      sidebarItems={sidebarItems}
      activeTab={activeTab}
      setActiveTab={handleTabChange}
      onLogout={logout}
      user={user}
      title="Plasiyer Panel"
      notificationCount={stats.pendingOrders}
    >
      {renderContent()}
      
      {/* Customer Detail Modal */}
      <CustomerDetailModal
        customer={selectedCustomer}
        isOpen={modalOpen}
        onClose={handleCloseModal}
        deliveries={deliveries}
        orders={orders}
        onSave={handleSaveCustomer}
      />
    </DashboardLayout>
  );
};

// ============================================
// SAYFA BİLEŞENLERİ
// ============================================

// Dashboard Page
const DashboardPage = ({ stats, customers, search, setSearch, deliveries, orders, onViewDetail, onCall, onMessage }) => (
  <div className="space-y-6" data-testid="sales-dashboard">
    <PageHeader title="Plasiyer" subtitle="Ana Sayfa / Plasiyer" />

    {/* Search & Filter */}
    <div className="flex items-center gap-3">
      <div className="relative flex-1">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          type="text"
          placeholder="Urun ara..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
          data-testid="search-input"
        />
      </div>
      <button className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-600 hover:border-slate-300">
        Son Siparis Tarihine Gore
        <ChevronRight className="w-4 h-4 rotate-90" />
      </button>
      <button className="flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-600 hover:border-slate-300">
        <Filter className="w-4 h-4" />
        Filtre
      </button>
    </div>

    {/* Stats */}
    <div className="grid grid-cols-4 gap-4">
      <StatCard title="Toplam Satislar (L3M)" value={`${stats.totalSales.toLocaleString('tr-TR')} TL`} subtitle={`+${stats.totalCustomers} firma`} gradient={gradients.blue} />
      <StatCard title="Bekleyen Siparisler" value={`${stats.pendingOrders} Siparis`} subtitle="5.540 TL Toplam" icon={ShoppingBag} gradient={gradients.green} />
      <StatCard title="Onerilen Siparisler" value={`${stats.suggestedOrders} Firma`} subtitle="3.300 TL Tavsiye Edilen" icon={TrendingUp} gradient={gradients.amber} />
      <StatCard title="Iade Talepleri" value={`${stats.returnRequests} Firma`} subtitle="2.870 TL Kontrol Edilmeli" icon={RotateCcw} gradient={gradients.red} />
    </div>

    {/* Customer Grid */}
    <div className="grid grid-cols-2 gap-4">
      {customers.slice(0, 6).map((customer, idx) => (
        <CustomerCard 
          key={customer.id} 
          customer={customer} 
          index={idx}
          deliveries={deliveries}
          orders={orders}
          onCall={() => onCall?.(customer)}
          onMessage={() => onMessage?.(customer)}
          onViewDetail={() => onViewDetail?.(customer)}
        />
      ))}
    </div>
  </div>
);

// Customers Page
const CustomersPage = ({ customers, search, setSearch, deliveries, orders, onViewDetail, onCall, onMessage, salespersonId }) => {
  const [sortBy, setSortBy] = useState('name');
  const [viewMode, setViewMode] = useState('active');

  const sortedCustomers = [...customers].sort((a, b) => {
    switch (sortBy) {
      case 'pending_orders':
        return (b.pending_orders_count || 0) - (a.pending_orders_count || 0);
      case 'overdue':
        return (b.overdue_deliveries_count || 0) - (a.overdue_deliveries_count || 0);
      case 'last_order':
        return (a.days_since_last_order || 999) - (b.days_since_last_order || 999);
      default:
        return (a.name || '').localeCompare(b.name || '', 'tr');
    }
  });

  return (
    <div className="space-y-6" data-testid="customers-page">
      <PageHeader title="Musteriler" subtitle="Ana Sayfa / Musteriler" />

      <div className="inline-flex rounded-2xl bg-slate-100 p-1" data-testid="customers-view-switcher">
        <button
          type="button"
          onClick={() => setViewMode('active')}
          className={`rounded-2xl px-4 py-2 text-sm font-medium transition-colors ${
            viewMode === 'active' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
          }`}
          data-testid="customers-view-active-button"
        >
          Aktif Müşteriler
        </button>
        <button
          type="button"
          onClick={() => setViewMode('draft')}
          className={`rounded-2xl px-4 py-2 text-sm font-medium transition-colors ${
            viewMode === 'draft' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
          }`}
          data-testid="customers-view-draft-button"
        >
          Draft Müşteriler
        </button>
      </div>

      {viewMode === 'draft' ? (
        <DraftCustomersManager salespersonId={salespersonId} />
      ) : (
        <>
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                placeholder="Musteri ara..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                data-testid="customer-search-input"
              />
            </div>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm text-slate-600 focus:outline-none focus:ring-2 focus:ring-orange-500"
              data-testid="sort-dropdown"
            >
              <option value="name">İsme Göre</option>
              <option value="pending_orders">Bekleyen Siparişler</option>
              <option value="overdue">Vadesi Geçenler</option>
              <option value="last_order">Son Sipariş Tarihi</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="bg-white border border-slate-200 rounded-xl p-3">
              <p className="text-xs text-slate-500">Toplam Müşteri</p>
              <p className="text-xl font-bold text-slate-800">{customers.length}</p>
            </div>
            <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3">
              <p className="text-xs text-emerald-600">Bekleyen Sipariş</p>
              <p className="text-xl font-bold text-emerald-700">
                {customers.reduce((sum, c) => sum + (c.pending_orders_count || 0), 0)}
              </p>
            </div>
            <div className="bg-red-50 border border-red-200 rounded-xl p-3">
              <p className="text-xs text-red-600">Vadesi Geçmiş</p>
              <p className="text-xl font-bold text-red-700">
                {customers.reduce((sum, c) => sum + (c.overdue_deliveries_count || 0), 0)}
              </p>
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-3">
              <p className="text-xs text-amber-600">7+ Gün Sipariş Yok</p>
              <p className="text-xl font-bold text-amber-700">
                {customers.filter(c => (c.days_since_last_order || 999) > 7).length}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            {sortedCustomers.map((customer, idx) => (
              <CustomerCard
                key={customer.id}
                customer={customer}
                index={idx}
                deliveries={deliveries}
                orders={orders}
                onCall={() => onCall?.(customer)}
                onMessage={() => onMessage?.(customer)}
                onViewDetail={() => onViewDetail?.(customer)}
              />
            ))}
          </div>

          {customers.length === 0 && (
            <EmptyState icon={Users} title="Musteri bulunamadi" />
          )}
        </>
      )}
    </div>
  );
};

// Deliveries Page
const DeliveriesPage = ({ deliveries }) => (
  <div className="space-y-6" data-testid="deliveries-page">
    <PageHeader title="Teslimatlar" subtitle="Ana Sayfa / Teslimatlar" />

    {deliveries.length === 0 ? (
      <EmptyState icon={Truck} title="Teslimat bulunamadi" />
    ) : (
      <div className="space-y-3">
        {deliveries.map(d => (
          <div key={d.id} className="bg-white border border-slate-200 rounded-2xl p-4">
            <div className="flex justify-between items-center mb-2">
              <div>
                <h3 className="font-bold text-slate-900">{d.customer_name || 'Musteri'}</h3>
                <p className="text-xs text-slate-500">{d.invoice_no}</p>
              </div>
              <Badge variant={
                d.acceptance_status === 'accepted' ? 'success' :
                d.acceptance_status === 'rejected' ? 'danger' : 'warning'
              }>
                {d.acceptance_status === 'accepted' ? 'Kabul Edildi' : 
                 d.acceptance_status === 'rejected' ? 'Reddedildi' : 'Bekliyor'}
              </Badge>
            </div>
            <p className="text-sm text-slate-500">
              {d.items?.length || 0} urun - {d.delivery_type === 'route' ? 'Rut' : 'Rut Disi'}
            </p>
          </div>
        ))}
      </div>
    )}
  </div>
);

// Analytics Page (Placeholder)
const AnalyticsPage = () => (
  <div className="space-y-6" data-testid="analytics-page">
    <PageHeader title="Analizler" subtitle="Ana Sayfa / Analizler" />
    <EmptyState icon={BarChart3} title="Analiz modulu yakin zamanda eklenecek" />
  </div>
);

// Returns Page (Placeholder)
const ReturnsPage = () => (
  <div className="space-y-6" data-testid="returns-page">
    <PageHeader title="Iade Talepleri" subtitle="Ana Sayfa / Iade Talepleri" />
    <EmptyState icon={RotateCcw} title="Henuz iade talebi yok" />
  </div>
);

export default PlasiyerDashboardShell;
