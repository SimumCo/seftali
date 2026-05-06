import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { sfSalesAPI } from '../../services/seftaliApi';
import { toast } from 'sonner';
import {
  Map, List, Navigation, Phone, MessageCircle,
  RefreshCw, Check, Clock, ChevronRight, X,
  MapPin, Zap,
} from 'lucide-react';
import RouteActionModal from './RouteActionModal';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
  iconUrl: require('leaflet/dist/images/marker-icon.png'),
  shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

const dayLabels = {
  MON: 'Pazartesi', TUE: 'Salı', WED: 'Çarşamba',
  THU: 'Perşembe', FRI: 'Cuma', SAT: 'Cumartesi', SUN: 'Pazar',
};

const monthsTr = ['Ocak','Şubat','Mart','Nisan','Mayıs','Haziran','Temmuz','Ağustos','Eylül','Ekim','Kasım','Aralık'];

function createMarkerIcon(order, isVisited) {
  const bg = isVisited ? '#10b981' : '#f97316';
  const html = `
    <div style="
      width:34px;height:34px;border-radius:50% 50% 50% 0;
      background:${bg};border:3px solid white;
      box-shadow:0 2px 8px rgba(0,0,0,0.35);
      display:flex;align-items:center;justify-content:center;
      color:white;font-weight:700;font-size:13px;
      transform:rotate(-45deg);
    ">
      <span style="transform:rotate(45deg)">${order}</span>
    </div>`;
  return L.divIcon({ className: '', html, iconSize: [34, 34], iconAnchor: [17, 34], popupAnchor: [0, -36] });
}

function AutoFitBounds({ positions }) {
  const map = useMap();
  useEffect(() => {
    if (positions.length === 0) return;
    if (positions.length === 1) {
      map.setView(positions[0], 14);
      return;
    }
    map.fitBounds(L.latLngBounds(positions), { padding: [48, 48] });
  }, [positions, map]);
  return null;
}

// ─── Sayılı kare rozet ────────────────────────────────────────────────────────
const OrderBadge = ({ order, variant = 'pending' }) => {
  const cls = variant === 'visited'
    ? 'bg-emerald-500 text-white'
    : 'bg-orange-500 text-white';
  return (
    <div className={`flex-shrink-0 w-11 h-11 rounded-lg flex items-center justify-center text-base font-bold shadow-sm ${cls}`}>
      {order}
    </div>
  );
};

// ─── Tek satır müşteri kartı ──────────────────────────────────────────────────
const RouteListItem = ({ customer, variant, onClick, testId }) => {
  const isVisited = variant === 'visited';
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full flex items-center gap-4 px-4 py-3.5 bg-white hover:bg-slate-50 transition-colors text-left border-b border-slate-100 last:border-b-0"
      data-testid={testId}
    >
      <OrderBadge order={customer.visit_order} variant={variant} />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-slate-900 truncate" data-testid={`${testId}-name`}>
          {customer.name}
        </p>
        <p className="text-sm text-slate-400 truncate">
          {customer.district || customer.address || 'Konum yok'}
        </p>
      </div>
      <div className="flex-shrink-0">
        {isVisited
          ? <Check className="w-5 h-5 text-emerald-500" />
          : <ChevronRight className="w-5 h-5 text-orange-500" />}
      </div>
    </button>
  );
};

// ─── Liste bölümü ─────────────────────────────────────────────────────────────
const RouteSection = ({ title, accentColor, customers, variant, onItemClick, emptyText, testId }) => {
  if (customers.length === 0) return null;
  const headerBg = accentColor === 'orange'
    ? 'bg-orange-50 text-orange-700 border-orange-100'
    : 'bg-emerald-50 text-emerald-700 border-emerald-100';
  return (
    <section className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden" data-testid={testId}>
      <div className={`px-4 py-2.5 text-sm font-semibold border-b ${headerBg}`}>
        {title}
      </div>
      <div>
        {customers.map((c) => (
          <RouteListItem
            key={c.id}
            customer={c}
            variant={variant}
            onClick={() => onItemClick(c)}
            testId={`route-item-${c.id}`}
          />
        ))}
      </div>
      {customers.length === 0 && (
        <div className="p-6 text-center text-sm text-slate-400">{emptyText}</div>
      )}
    </section>
  );
};

// ─── Segmentli özet barı ──────────────────────────────────────────────────────
const RouteSummaryBar = ({ pending, visited }) => {
  const total = Math.max(pending + visited, 1);
  const pendingPct = (pending / total) * 100;
  const visitedPct = 100 - pendingPct;
  return (
    <div className="flex w-full rounded-xl overflow-hidden shadow-sm" data-testid="route-summary-bar">
      <div
        className="bg-orange-500 text-white px-4 py-2.5 text-sm font-semibold flex items-center justify-center transition-all"
        style={{ width: `${Math.max(pendingPct, 18)}%` }}
        data-testid="summary-pending"
      >
        Bekleyen: {pending} Nokta
      </div>
      <div
        className="bg-emerald-500 text-white px-4 py-2.5 text-sm font-semibold flex items-center justify-center transition-all"
        style={{ width: `${Math.max(visitedPct, 18)}%` }}
        data-testid="summary-visited"
      >
        Gidilen: {visited} Nokta
      </div>
    </div>
  );
};

// ─── Ana Bileşen ──────────────────────────────────────────────────────────────
const RouteMapPage = ({ routeDay = 'MON' }) => {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [activeView, setActiveView] = useState('list');
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [actionItem, setActionItem] = useState(null);
  const [statusMap, setStatusMap] = useState({}); // { [id]: { status, visit_result, visited_at } }
  const [totalDistance, setTotalDistance] = useState(null);

  const fetchRoute = useCallback(async (optimize = false) => {
    if (optimize) setOptimizing(true);
    else setLoading(true);
    try {
      const res = await sfSalesAPI.getRouteMap(routeDay, optimize);
      const data = res.data?.data || {};
      const list = (data.customers || []).map((c, idx) => ({
        ...c,
        visit_order: c.visit_order || idx + 1,
      }));
      setCustomers(list);
      setTotalDistance(data.total_distance_km ?? null);
      if (optimize) toast.success(`Rota optimize edildi! ~${data.total_distance_km?.toFixed(1)} km`);
    } catch {
      toast.error('Rota verisi yüklenemedi');
    } finally {
      setLoading(false);
      setOptimizing(false);
    }
  }, [routeDay]);

  useEffect(() => { fetchRoute(false); }, [fetchRoute]);

  // routeDay değişiminde günler arası state sızıntısını önle
  useEffect(() => {
    setStatusMap({});
    setActionItem(null);
    setSelectedCustomer(null);
  }, [routeDay]);

  const isVisitedId = (id) => statusMap[id]?.status === 'visited';

  const toggleVisited = (customerId) => {
    const wasVisited = isVisitedId(customerId);
    setStatusMap(prev => ({
      ...prev,
      [customerId]: wasVisited
        ? { status: 'pending', visit_result: 'not_visited', visited_at: null }
        : { status: 'visited', visit_result: 'visited', visited_at: new Date().toISOString() },
    }));
    const c = customers.find(x => x.id === customerId);
    if (c) toast.success(wasVisited ? `${c.name} bekleyene alındı` : `${c.name} gidildi olarak işaretlendi`);
  };

  // RouteActionModal onaylandığında durumu güncelle
  const handleActionConfirm = (customerId, update) => {
    const next = {
      status: update.status,
      visit_result: update.visit_result,
      visited_at: update.status === 'visited' ? new Date().toISOString() : null,
    };
    setStatusMap(prev => ({ ...prev, [customerId]: next }));
    setActionItem(null);

    const messages = {
      visited: 'Nokta gidilmiş olarak işaretlendi',
      visited_without_invoice: 'Nokta fatura oluşturmadan gidilmiş olarak işaretlendi',
      not_visited: 'Nokta bekleyen listesinde bırakıldı',
    };
    toast.success(messages[update.visit_result] || 'Rut durumu güncellendi');
  };

  const handleOpenLocationById = (customerId) => {
    const c = customers.find(x => x.id === customerId);
    if (c) openGoogleMaps(c);
  };
  const handleOpenMessagesById = (customerId) => {
    const c = customers.find(x => x.id === customerId);
    if (c) openWhatsApp(c.phone);
  };
  const handleOpenInvoiceById = (customerId) => {
    const c = customers.find(x => x.id === customerId);
    if (c) toast.info(`${c.name} için fatura oluşturma akışı henüz bağlı değil`);
  };

  const openGoogleMaps = (customer) => {
    const lat = customer.location?.lat;
    const lng = customer.location?.lng;
    if (lat && lng) {
      window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`, '_blank');
    } else if (customer.address) {
      window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(customer.address)}`, '_blank');
    } else {
      toast.warning('Konum bilgisi bulunamadı');
    }
  };

  const openWhatsApp = (phone) => {
    if (!phone) { toast.warning('Telefon numarası yok'); return; }
    window.open(`https://wa.me/${phone.replace(/\D/g, '')}`, '_blank');
  };

  const openCall = (phone) => {
    if (!phone) { toast.warning('Telefon numarası yok'); return; }
    window.open(`tel:${phone}`, '_self');
  };

  const sortedCustomers = useMemo(
    () => [...customers].sort((a, b) => a.visit_order - b.visit_order),
    [customers]
  );

  const pendingCustomers = useMemo(
    () => sortedCustomers.filter(c => statusMap[c.id]?.status !== 'visited'),
    [sortedCustomers, statusMap]
  );
  const visitedCustomers = useMemo(
    () => sortedCustomers.filter(c => statusMap[c.id]?.status === 'visited'),
    [sortedCustomers, statusMap]
  );

  const mappedCustomers = useMemo(
    () => sortedCustomers.filter(c => c.location?.lat != null && c.location?.lng != null),
    [sortedCustomers]
  );
  const positions = useMemo(
    () => mappedCustomers.map(c => [c.location.lat, c.location.lng]),
    [mappedCustomers]
  );
  const mapCenter = positions.length > 0 ? positions[0] : [41.0082, 28.9784];

  // Tarih başlık metni: "6 Mayıs Çarşamba - 14 nokta"
  const headerSubtitle = useMemo(() => {
    const today = new Date();
    const dayCode = ['SUN','MON','TUE','WED','THU','FRI','SAT'][today.getDay()];
    const dateStr = dayCode === routeDay
      ? `${today.getDate()} ${monthsTr[today.getMonth()]} ${dayLabels[routeDay]}`
      : dayLabels[routeDay];
    return `${dateStr} • ${customers.length} nokta`;
  }, [routeDay, customers.length]);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-80 gap-4" data-testid="route-map-loading">
        <RefreshCw className="w-8 h-8 animate-spin text-orange-500" />
        <p className="text-slate-500">Rota yükleniyor...</p>
      </div>
    );
  }

  return (
    <div className="space-y-5" data-testid="route-map-page">

      {/* ─── Sayfa Başlığı ─── */}
      <div className="flex items-start justify-between gap-3 flex-wrap" data-testid="route-page-header">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Bugünün Noktaları</h1>
          <p className="text-sm text-slate-500 mt-1" data-testid="route-page-subtitle">
            {headerSubtitle}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Görünüm Seçici */}
          <div className="inline-flex bg-slate-100 rounded-xl p-1 gap-1">
            <button
              onClick={() => setActiveView('list')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeView === 'list' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
              }`}
              data-testid="view-list-button"
            >
              <List className="w-4 h-4" /> Liste
            </button>
            <button
              onClick={() => setActiveView('map')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                activeView === 'map' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
              }`}
              data-testid="view-map-button"
            >
              <Map className="w-4 h-4" /> Harita
            </button>
          </div>

          <button
            onClick={() => fetchRoute(true)}
            disabled={optimizing || customers.length === 0}
            className="flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm font-medium bg-slate-900 text-white disabled:opacity-50 hover:bg-slate-800 transition-colors"
            data-testid="optimize-route-button"
          >
            {optimizing
              ? <RefreshCw className="w-4 h-4 animate-spin" />
              : <Zap className="w-4 h-4" />}
            Optimize
          </button>
        </div>
      </div>

      {/* ─── Segmentli Özet Bar ─── */}
      {customers.length > 0 && (
        <RouteSummaryBar
          pending={pendingCustomers.length}
          visited={visitedCustomers.length}
        />
      )}

      {/* ─── Liste Görünümü ─── */}
      {activeView === 'list' && (
        <div className="space-y-4" data-testid="route-list">
          {customers.length === 0 ? (
            <div className="bg-white border border-slate-200 rounded-2xl p-12 text-center text-slate-400">
              <MapPin className="w-10 h-10 mx-auto mb-3 text-slate-300" />
              Bu gün için rota müşterisi bulunamadı.
            </div>
          ) : (
            <>
              <RouteSection
                title="Bekleyen Noktalar"
                accentColor="orange"
                customers={pendingCustomers}
                variant="pending"
                onItemClick={setActionItem}
                testId="section-pending"
              />
              <RouteSection
                title="Gidilmiş Noktalar"
                accentColor="green"
                customers={visitedCustomers}
                variant="visited"
                onItemClick={setSelectedCustomer}
                testId="section-visited"
              />
            </>
          )}
        </div>
      )}

      {/* ─── Harita Görünümü ─── */}
      {activeView === 'map' && (
        <div className="rounded-2xl overflow-hidden border border-slate-200 shadow-sm" style={{ height: '560px' }} data-testid="leaflet-map-container">
          {mappedCustomers.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full bg-slate-50 gap-3">
              <MapPin className="w-12 h-12 text-slate-300" />
              <p className="text-slate-500 text-sm">Haritada gösterilecek koordinat bulunamadı.</p>
              <p className="text-slate-400 text-xs">Müşteri profillerine konum eklendiğinde burada görünecek.</p>
            </div>
          ) : (
            <MapContainer
              center={mapCenter}
              zoom={13}
              style={{ height: '100%', width: '100%' }}
              data-testid="leaflet-map"
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              />
              <AutoFitBounds positions={positions} />
              {positions.length > 1 && (
                <Polyline
                  positions={positions}
                  pathOptions={{ color: '#f97316', weight: 3, opacity: 0.7, dashArray: '6 4' }}
                />
              )}
              {mappedCustomers.map(c => {
                const isVisited = isVisitedId(c.id);
                return (
                  <Marker
                    key={c.id}
                    position={[c.location.lat, c.location.lng]}
                    icon={createMarkerIcon(c.visit_order, isVisited)}
                    eventHandlers={{ click: () => (isVisited ? setSelectedCustomer(c) : setActionItem(c)) }}
                  >
                    <Popup>
                      <div className="min-w-[180px]">
                        <p className="font-bold text-slate-900 mb-1">{c.name}</p>
                        <p className="text-xs text-slate-500 mb-2">{c.address || 'Adres bilgisi yok'}</p>
                        <button
                          onClick={() => openGoogleMaps(c)}
                          className="w-full flex items-center justify-center gap-1 px-3 py-1.5 bg-orange-500 text-white text-xs rounded-lg font-medium"
                        >
                          <Navigation className="w-3 h-3" /> Yol Tarifi
                        </button>
                      </div>
                    </Popup>
                  </Marker>
                );
              })}
            </MapContainer>
          )}
          {totalDistance != null && (
            <p className="text-xs text-slate-500 mt-2 text-right">
              Toplam tahmini mesafe: ~{totalDistance.toFixed(1)} km
            </p>
          )}
        </div>
      )}

      {/* ─── Bekleyen Müşteri İşlem Modali ─── */}
      <RouteActionModal
        isOpen={Boolean(actionItem)}
        item={actionItem ? { ...actionItem, visit_result: statusMap[actionItem.id]?.visit_result || 'not_visited' } : null}
        onClose={() => setActionItem(null)}
        onConfirm={handleActionConfirm}
        onOpenLocation={handleOpenLocationById}
        onOpenMessages={handleOpenMessagesById}
        onOpenInvoice={handleOpenInvoiceById}
      />

      {/* ─── Gidilmiş Müşteri Detay Drawer ─── */}
      {selectedCustomer && (
        <CustomerDrawer
          customer={selectedCustomer}
          isVisited={isVisitedId(selectedCustomer.id)}
          onClose={() => setSelectedCustomer(null)}
          onToggleVisited={() => toggleVisited(selectedCustomer.id)}
          onNavigate={() => openGoogleMaps(selectedCustomer)}
          onCall={() => openCall(selectedCustomer.phone)}
          onWhatsApp={() => openWhatsApp(selectedCustomer.phone)}
        />
      )}
    </div>
  );
};

// ─── Müşteri Detay Drawer ─────────────────────────────────────────────────────
const CustomerDrawer = ({ customer, isVisited, onClose, onToggleVisited, onNavigate, onCall, onWhatsApp }) => (
  <div
    className="fixed inset-0 z-50 flex justify-end bg-slate-950/40 backdrop-blur-sm"
    onClick={onClose}
    data-testid="customer-drawer-overlay"
  >
    <aside
      className="h-full w-full max-w-sm bg-white shadow-2xl overflow-y-auto"
      onClick={e => e.stopPropagation()}
      data-testid="customer-drawer"
    >
      <div className="flex items-start justify-between p-5 border-b border-slate-100">
        <div>
          <span className="text-xs font-semibold uppercase tracking-widest text-slate-400">Durak Detayı</span>
          <h2 className="text-xl font-bold text-slate-900 mt-1">{customer.name}</h2>
          <p className="text-sm text-slate-400 mt-0.5">#{customer.visit_order}. durak</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-xl border border-slate-200 text-slate-500 hover:bg-slate-50"
          data-testid="customer-drawer-close"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="px-5 pt-4">
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold ${
          isVisited ? 'bg-emerald-100 text-emerald-700' : 'bg-orange-100 text-orange-700'
        }`} data-testid="customer-drawer-status">
          {isVisited ? <Check className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
          {isVisited ? 'Gidildi' : 'Bekliyor'}
        </span>
      </div>

      <div className="p-5 space-y-3">
        <InfoField label="Adres" value={customer.address || 'Adres bilgisi yok'} />
        <InfoField label="İlçe" value={customer.district || 'Belirtilmemiş'} />
        <InfoField label="Telefon" value={customer.phone || 'Belirtilmemiş'} />
        {customer.location?.lat != null ? (
          <InfoField label="Koordinat" value={`${customer.location.lat.toFixed(5)}, ${customer.location.lng.toFixed(5)}`} />
        ) : (
          <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-700">
            Bu müşteri için harita koordinatı tanımlı değil.
          </div>
        )}
      </div>

      <div className="p-5 space-y-3 border-t border-slate-100">
        <button
          onClick={onNavigate}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-orange-500 text-white rounded-xl font-semibold hover:bg-orange-600 transition-colors"
          data-testid="navigate-button"
        >
          <Navigation className="w-4 h-4" /> Google Maps ile Git
        </button>

        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={onCall}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-100 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-200 transition-colors"
            data-testid="call-button"
          >
            <Phone className="w-4 h-4" /> Ara
          </button>
          <button
            onClick={onWhatsApp}
            className="flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-50 text-emerald-700 rounded-xl text-sm font-medium hover:bg-emerald-100 transition-colors border border-emerald-200"
            data-testid="whatsapp-button"
          >
            <MessageCircle className="w-4 h-4" /> WhatsApp
          </button>
        </div>

        <button
          onClick={onToggleVisited}
          className={`w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl font-semibold transition-colors ${
            isVisited
              ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              : 'bg-emerald-500 text-white hover:bg-emerald-600'
          }`}
          data-testid="toggle-visited-button"
        >
          <Check className="w-4 h-4" />
          {isVisited ? 'Bekleyene Al' : 'Gidildi Olarak İşaretle'}
        </button>
      </div>
    </aside>
  </div>
);

const InfoField = ({ label, value }) => (
  <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
    <p className="text-xs font-medium uppercase tracking-widest text-slate-400">{label}</p>
    <p className="mt-1 text-sm font-semibold text-slate-900">{value}</p>
  </div>
);

export default RouteMapPage;
