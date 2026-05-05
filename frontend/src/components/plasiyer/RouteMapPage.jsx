import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { sfSalesAPI } from '../../services/seftaliApi';
import { toast } from 'sonner';
import {
  Map, List, Navigation, Phone, MessageCircle,
  RefreshCw, Check, Clock, ChevronRight, X,
  Route, MapPin, Zap,
} from 'lucide-react';

// Leaflet ikon düzeltmesi (CRA'da gerekli)
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

// ─── Özel renkli harita ikonu ────────────────────────────────────────────────
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

// ─── Harita sınırlarını otomatik ayarla ──────────────────────────────────────
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

// ─── Ana Bileşen ─────────────────────────────────────────────────────────────
const RouteMapPage = ({ routeDay = 'MON' }) => {
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [activeView, setActiveView] = useState('map'); // 'map' | 'list'
  const [selectedCustomer, setSelectedCustomer] = useState(null);
  const [visitedIds, setVisitedIds] = useState(new Set());
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
      if (optimize) toast.success(`Rota optimize edildi! Toplam ~${data.total_distance_km?.toFixed(1)} km`);
    } catch {
      toast.error('Rota verisi yüklenemedi');
    } finally {
      setLoading(false);
      setOptimizing(false);
    }
  }, [routeDay]);

  useEffect(() => {
    fetchRoute(false);
  }, [fetchRoute]);

  const toggleVisited = (customerId) => {
    setVisitedIds(prev => {
      const next = new Set(prev);
      if (next.has(customerId)) next.delete(customerId);
      else next.add(customerId);
      return next;
    });
    const c = customers.find(x => x.id === customerId);
    if (c) toast.success(visitedIds.has(customerId) ? `${c.name} bekleyene alındı` : `${c.name} gidildi olarak işaretlendi`);
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

  // Hesaplanan değerler
  const sortedCustomers = useMemo(
    () => [...customers].sort((a, b) => a.visit_order - b.visit_order),
    [customers]
  );

  const mappedCustomers = useMemo(
    () => sortedCustomers.filter(c => c.location?.lat != null && c.location?.lng != null),
    [sortedCustomers]
  );

  const positions = useMemo(
    () => mappedCustomers.map(c => [c.location.lat, c.location.lng]),
    [mappedCustomers]
  );

  const visitedCount = useMemo(() => [...visitedIds].filter(id => customers.find(c => c.id === id)).length, [visitedIds, customers]);
  const pendingCount = customers.length - visitedCount;
  const progressPct = customers.length > 0 ? Math.round((visitedCount / customers.length) * 100) : 0;

  // Default harita merkezi (İstanbul)
  const mapCenter = positions.length > 0 ? positions[0] : [41.0082, 28.9784];

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center h-80 gap-4" data-testid="route-map-loading">
        <RefreshCw className="w-8 h-8 animate-spin text-orange-500" />
        <p className="text-slate-500">Rota yükleniyor...</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="route-map-page">

      {/* ─── Başlık & İstatistikler ─── */}
      <div className="bg-gradient-to-r from-orange-500 to-amber-500 rounded-2xl p-5 text-white" data-testid="route-map-header">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Route className="w-5 h-5" />
              Rota Haritası
            </h1>
            <p className="text-orange-100 text-sm mt-0.5">
              {dayLabels[routeDay]} · {customers.length} durak
              {totalDistance != null && ` · ~${totalDistance.toFixed(1)} km`}
            </p>
          </div>

          <button
            onClick={() => fetchRoute(true)}
            disabled={optimizing}
            className="flex items-center gap-2 px-3 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-sm font-medium transition-colors"
            data-testid="optimize-route-button"
          >
            {optimizing
              ? <RefreshCw className="w-4 h-4 animate-spin" />
              : <Zap className="w-4 h-4" />}
            {optimizing ? 'Optimize ediliyor...' : 'Optimize Et'}
          </button>
        </div>

        {/* İlerleme Barı */}
        <div className="flex items-center gap-3">
          <div className="flex-1 bg-white/20 rounded-full h-2.5 overflow-hidden">
            <div
              className="bg-white h-full rounded-full transition-all duration-500"
              style={{ width: `${progressPct}%` }}
              data-testid="route-progress-bar"
            />
          </div>
          <span className="text-sm font-semibold whitespace-nowrap" data-testid="route-progress-label">
            {visitedCount}/{customers.length} tamamlandı
          </span>
        </div>

        {/* Özet Kutuları */}
        <div className="grid grid-cols-3 gap-2 mt-3">
          <div className="bg-white/15 rounded-xl p-2 text-center">
            <p className="text-xs text-orange-100">Bekleyen</p>
            <p className="text-lg font-bold" data-testid="pending-count">{pendingCount}</p>
          </div>
          <div className="bg-white/15 rounded-xl p-2 text-center">
            <p className="text-xs text-orange-100">Gidilen</p>
            <p className="text-lg font-bold" data-testid="visited-count">{visitedCount}</p>
          </div>
          <div className="bg-white/15 rounded-xl p-2 text-center">
            <p className="text-xs text-orange-100">Haritada</p>
            <p className="text-lg font-bold" data-testid="mapped-count">{mappedCustomers.length}</p>
          </div>
        </div>
      </div>

      {/* ─── Görünüm Seçici ─── */}
      <div className="inline-flex bg-slate-100 rounded-2xl p-1 gap-1" data-testid="view-switcher">
        <button
          onClick={() => setActiveView('map')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
            activeView === 'map' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
          }`}
          data-testid="view-map-button"
        >
          <Map className="w-4 h-4" /> Harita
        </button>
        <button
          onClick={() => setActiveView('list')}
          className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-colors ${
            activeView === 'list' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500'
          }`}
          data-testid="view-list-button"
        >
          <List className="w-4 h-4" /> Liste
        </button>
      </div>

      {/* ─── Harita Görünümü ─── */}
      {activeView === 'map' && (
        <div className="rounded-2xl overflow-hidden border border-slate-200 shadow-sm" style={{ height: '480px' }} data-testid="leaflet-map-container">
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

              {/* Rota çizgisi */}
              {positions.length > 1 && (
                <Polyline
                  positions={positions}
                  pathOptions={{ color: '#f97316', weight: 3, opacity: 0.7, dashArray: '6 4' }}
                />
              )}

              {/* Müşteri işaretleri */}
              {mappedCustomers.map(c => {
                const isVisited = visitedIds.has(c.id);
                return (
                  <Marker
                    key={c.id}
                    position={[c.location.lat, c.location.lng]}
                    icon={createMarkerIcon(c.visit_order, isVisited)}
                    eventHandlers={{ click: () => setSelectedCustomer(c) }}
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
        </div>
      )}

      {/* ─── Liste Görünümü ─── */}
      {activeView === 'list' && (
        <div className="space-y-2" data-testid="route-list">
          {sortedCustomers.length === 0 && (
            <div className="bg-white border border-slate-200 rounded-2xl p-8 text-center text-slate-400">
              Bu gün için rota müşterisi bulunamadı.
            </div>
          )}
          {sortedCustomers.map((c) => {
            const isVisited = visitedIds.has(c.id);
            const hasCoords = c.location?.lat != null;
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => setSelectedCustomer(c)}
                className={`w-full flex items-center gap-4 px-5 py-4 bg-white border rounded-2xl text-left transition-colors ${
                  isVisited ? 'border-emerald-200 bg-emerald-50/50' : 'border-slate-200'
                }`}
                data-testid={`route-list-item-${c.id}`}
              >
                {/* Sıra Numarası */}
                <div className={`flex-shrink-0 w-10 h-10 rounded-2xl flex items-center justify-center text-sm font-bold ${
                  isVisited ? 'bg-emerald-500 text-white' : 'bg-orange-500 text-white'
                }`}>
                  {isVisited ? <Check className="w-4 h-4" /> : c.visit_order}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-slate-900 truncate">{c.name}</p>
                  <p className="text-sm text-slate-400 truncate">
                    {c.district || c.address || 'Konum bilgisi yok'}
                  </p>
                </div>

                <div className="flex items-center gap-2 flex-shrink-0">
                  {!hasCoords && (
                    <span className="text-xs text-amber-500 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
                      Koordinat yok
                    </span>
                  )}
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </div>
              </button>
            );
          })}
        </div>
      )}

      {/* ─── Müşteri Detay Drawer ─── */}
      {selectedCustomer && (
        <CustomerDrawer
          customer={selectedCustomer}
          isVisited={visitedIds.has(selectedCustomer.id)}
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
      {/* Başlık */}
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

      {/* Durum Rozeti */}
      <div className="px-5 pt-4">
        <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-semibold ${
          isVisited ? 'bg-emerald-100 text-emerald-700' : 'bg-orange-100 text-orange-700'
        }`} data-testid="customer-drawer-status">
          {isVisited ? <Check className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
          {isVisited ? 'Gidildi' : 'Bekliyor'}
        </span>
      </div>

      {/* Bilgi Alanları */}
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

      {/* Aksiyon Butonları */}
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
