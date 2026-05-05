import React, { useEffect, useMemo, useState } from 'react';
import { sfSalesAPI } from '../../services/seftaliApi';
import { toast } from 'sonner';
import {
  CalendarDays,
  Check,
  ChevronRight,
  X,
} from 'lucide-react';
import RouteActionModal from './RouteActionModal';
import { Loading } from '../ui/DesignSystem';

const dayLabels = {
  SUN: 'Pazar',
  MON: 'Pazartesi',
  TUE: 'Salı',
  WED: 'Çarşamba',
  THU: 'Perşembe',
  FRI: 'Cuma',
  SAT: 'Cumartesi',
};

const monthLabels = [
  'Ocak',
  'Şubat',
  'Mart',
  'Nisan',
  'Mayıs',
  'Haziran',
  'Temmuz',
  'Ağustos',
  'Eylül',
  'Ekim',
  'Kasım',
  'Aralık',
];

const orderStatusLabels = {
  submitted: 'Sipariş girildi',
  draft_available: 'Taslak hazır',
  no_order: 'İşlem bekliyor',
};

const statusStyles = {
  pending: {
    badge: 'bg-orange-500 text-white',
    iconWrap: 'bg-orange-50 text-orange-500',
    hover: 'hover:bg-orange-50/70 focus-visible:ring-orange-200',
    section: 'bg-orange-50/80 text-orange-700',
  },
  visited: {
    badge: 'bg-emerald-500 text-white',
    iconWrap: 'bg-emerald-50 text-emerald-500',
    hover: 'hover:bg-emerald-50/70 focus-visible:ring-emerald-200',
    section: 'bg-emerald-50/80 text-emerald-700',
  },
};

const formatRouteDateLabel = (date = new Date()) => {
  const weekday = dayLabels[['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'][date.getDay()]];
  const month = monthLabels[date.getMonth()];
  return `${date.getDate()} ${month} ${weekday}`;
};

const normalizeRouteItems = (customers = []) =>
  customers
    .map((customer, index) => {
      const rawVisitOrder = Number(
        customer.visit_order ?? customer.route_plan?.sequence ?? customer.route_order
      );
      const visitOrder = Number.isFinite(rawVisitOrder) && rawVisitOrder > 0 ? rawVisitOrder : index + 1;
      const status = customer.status || (['submitted', 'draft_available'].includes(customer.order_status) ? 'visited' : 'pending');

      return {
        id: customer.id || `route-item-${index}`,
        customer_name: customer.customer_name || customer.name || 'İsimsiz nokta',
        district:
          customer.district ||
          customer.location?.district ||
          customer.location?.address ||
          customer.address ||
          'Konum bilgisi yok',
        visit_order: visitOrder,
        status,
        visit_result: customer.visit_result || (status === 'visited' ? 'visited' : 'not_visited'),
        order_status: customer.order_status || 'no_order',
        phone: customer.phone || '',
        address: customer.location?.address || customer.address || 'Adres bilgisi yok',
        location: customer.location || null,
        source: customer,
        sourceIndex: index,
      };
    })
    .sort((a, b) => a.visit_order - b.visit_order || a.sourceIndex - b.sourceIndex);

const RouteSummaryBar = ({ pendingCount, visitedCount, totalPoints }) => {
  const computedTotal = totalPoints > 0 ? totalPoints : pendingCount + visitedCount;
  const pendingWidth = computedTotal > 0 ? (pendingCount / computedTotal) * 100 : 50;
  const visitedWidth = computedTotal > 0 ? (visitedCount / computedTotal) * 100 : 50;

  return (
    <div
      className="overflow-hidden rounded-[22px] border border-slate-200 bg-white p-2 shadow-[0_18px_45px_-30px_rgba(15,23,42,0.35)]"
      data-testid="route-summary-bar"
    >
      <div className="flex h-14 overflow-hidden rounded-[18px] bg-slate-100" data-testid="route-summary-progress-track">
        <div
          className="flex items-center bg-orange-500 px-5 text-sm font-semibold text-white transition-all duration-500 ease-out"
          style={{ width: `${pendingWidth}%` }}
          data-testid="route-summary-pending"
        >
          <span className="truncate whitespace-nowrap">Bekleyen: {pendingCount} Nokta</span>
        </div>
        <div
          className="flex items-center bg-emerald-500 px-5 text-sm font-semibold text-white transition-all duration-500 ease-out"
          style={{ width: `${visitedWidth}%` }}
          data-testid="route-summary-visited"
        >
          <span className="truncate whitespace-nowrap">Gidilen: {visitedCount} Nokta</span>
        </div>
      </div>
    </div>
  );
};

const RouteListItem = ({ item, onOpen }) => {
  const itemStyles = statusStyles[item.status] || statusStyles.pending;
  const isVisited = item.status === 'visited';

  return (
    <button
      type="button"
      onClick={() => onOpen(item)}
      className={`flex w-full items-center gap-4 px-5 py-4 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 ${itemStyles.hover}`}
      data-testid={`route-list-item-${item.status}-${item.id}`}
    >
      <div
        className={`flex h-12 w-12 flex-shrink-0 items-center justify-center rounded-2xl text-lg font-bold ${itemStyles.badge}`}
        data-testid={`route-visit-order-${item.id}`}
      >
        {item.visit_order}
      </div>

      <div className="min-w-0 flex-1">
        <p className="truncate text-base font-semibold text-slate-900" data-testid={`route-customer-name-${item.id}`}>
          {item.customer_name}
        </p>
        <p className="mt-1 truncate text-sm text-slate-500" data-testid={`route-customer-district-${item.id}`}>
          {item.district}
        </p>
      </div>

      <div
        className={`flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-2xl ${itemStyles.iconWrap}`}
        data-testid={`route-list-action-${item.id}`}
      >
        {isVisited ? <Check className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
      </div>
    </button>
  );
};

const RouteSection = ({ title, status, items, onOpen }) => {
  const itemStyles = statusStyles[status] || statusStyles.pending;

  return (
    <section
      className="overflow-hidden rounded-[26px] border border-slate-200 bg-white shadow-[0_18px_45px_-30px_rgba(15,23,42,0.35)]"
      data-testid={`route-section-${status}`}
    >
      <div className={`border-b border-slate-100 px-5 py-4 text-lg font-semibold ${itemStyles.section}`}>
        {title}
      </div>

      {items.length === 0 ? (
        <div className="px-5 py-8 text-sm text-slate-500" data-testid={`route-section-empty-${status}`}>
          Bu bölümde gösterilecek nokta bulunmuyor.
        </div>
      ) : (
        <div className="divide-y divide-slate-100">
          {items.map((item) => (
            <RouteListItem key={item.id} item={item} onOpen={onOpen} />
          ))}
        </div>
      )}
    </section>
  );
};

const DetailField = ({ label, value, testId }) => (
  <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3" data-testid={testId}>
    <p className="text-xs font-medium uppercase tracking-[0.18em] text-slate-400">{label}</p>
    <p className="mt-2 text-sm font-semibold text-slate-900">{value}</p>
  </div>
);

const RouteDetailDrawer = ({ item, onClose, routeDay }) => {
  if (!item) {
    return null;
  }

  const isVisited = item.status === 'visited';
  const itemStyles = statusStyles[item.status] || statusStyles.pending;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-slate-950/35 backdrop-blur-[2px]"
      onClick={onClose}
      data-testid="route-detail-drawer-overlay"
    >
      <aside
        className="h-full w-full max-w-md overflow-y-auto bg-white px-6 py-6 shadow-2xl"
        onClick={(event) => event.stopPropagation()}
        data-testid="route-detail-drawer"
      >
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 pb-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Nokta Detayı</p>
            <h2 className="mt-2 text-2xl font-bold text-slate-900">{item.customer_name}</h2>
            <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">
              <CalendarDays className="h-4 w-4" />
              <span data-testid="route-detail-date">{formatRouteDateLabel()} • {dayLabels[routeDay] || routeDay}</span>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="rounded-2xl border border-slate-200 p-2 text-slate-500 transition-colors hover:bg-slate-50"
            data-testid="route-detail-close-button"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-6 space-y-4">
          <div className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${itemStyles.section}`} data-testid="route-detail-status-badge">
            {isVisited ? 'Gidilmiş nokta' : 'Bekleyen nokta'}
          </div>

          <DetailField label="Ziyaret sırası" value={`${item.visit_order}. durak`} testId="route-detail-visit-order" />
          <DetailField label="İlçe / Konum" value={item.district} testId="route-detail-district" />
          <DetailField label="Adres" value={item.address} testId="route-detail-address" />
          <DetailField label="Bugünkü durum" value={orderStatusLabels[item.order_status] || 'İşlem bekliyor'} testId="route-detail-order-status" />
          <DetailField label="Telefon" value={item.phone || 'Telefon bilgisi yok'} testId="route-detail-phone" />

          <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-500" data-testid="route-detail-readonly-note">
            Bu görünüm şu an read-only olarak hazırlanmıştır. Sipariş/ziyaret detay alanları bir sonraki adımda ileteceğiniz kapsamla genişletilebilir.
          </div>
        </div>
      </aside>
    </div>
  );
};

const RutPage = ({ routeDay = 'MON', todayCustomers = [] }) => {
  const fallbackRouteItems = useMemo(() => normalizeRouteItems(todayCustomers), [todayCustomers]);
  const [routeItems, setRouteItems] = useState(fallbackRouteItems);
  const [loading, setLoading] = useState(true);
  const [selectedRouteItem, setSelectedRouteItem] = useState(null);
  const [selectedActionItem, setSelectedActionItem] = useState(null);

  useEffect(() => {
    let mounted = true;

    const fetchRouteItems = async () => {
      setLoading(true);
      try {
        const response = await sfSalesAPI.getRouteCustomers(routeDay);
        if (!mounted) {
          return;
        }
        setRouteItems(normalizeRouteItems(response.data?.data || []));
      } catch {
        if (!mounted) {
          return;
        }
        setRouteItems(fallbackRouteItems);
        toast.error('Rut verisi yüklenemedi');
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchRouteItems();

    return () => {
      mounted = false;
    };
  }, [fallbackRouteItems, routeDay]);

  const findRouteItemById = (customerId) => routeItems.find((item) => item.id === customerId);

  const openLocation = (customerId) => {
    const currentItem = findRouteItemById(customerId);

    if (!currentItem) {
      toast.error('Nokta bulunamadı');
      return;
    }

    const lat = currentItem.location?.lat;
    const lng = currentItem.location?.lng;

    if (typeof lat === 'number' && typeof lng === 'number') {
      window.open(`https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`, '_blank');
      return;
    }

    if (currentItem.address && currentItem.address !== 'Adres bilgisi yok') {
      window.open(`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(currentItem.address)}`, '_blank');
      return;
    }

    toast.warning('Konum bilgisi bulunamadı');
  };

  const openMessages = (customerId) => {
    const currentItem = findRouteItemById(customerId);

    if (!currentItem) {
      toast.error('Nokta bulunamadı');
      return;
    }

    const phoneNumber = (currentItem.phone || '').replace(/\D/g, '');
    if (phoneNumber) {
      window.open(`https://wa.me/${phoneNumber}`, '_blank');
      return;
    }

    toast.info('Mesaj akışı henüz bağlı değil');
  };

  const openInvoice = (customerId) => {
    const currentItem = findRouteItemById(customerId);

    if (!currentItem) {
      toast.error('Nokta bulunamadı');
      return;
    }

    toast.info(`${currentItem.customer_name} için fatura oluşturma akışı henüz bağlı değil`);
  };

  const handlePendingItemOpen = (item) => {
    setSelectedActionItem(item);
  };

  const handleVisitedItemOpen = (item) => {
    setSelectedRouteItem(item);
  };

  const handleActionConfirm = (customerId, update) => {
    setRouteItems((currentItems) =>
      currentItems.map((item) => (item.id === customerId ? { ...item, ...update } : item))
    );
    setSelectedActionItem(null);

    const successMessages = {
      visited: 'Nokta gidilmiş olarak işaretlendi',
      visited_without_invoice: 'Nokta fatura oluşturmadan gidilmiş olarak işaretlendi',
      not_visited: 'Nokta bekleyen listesinde bırakıldı',
    };

    toast.success(successMessages[update.visit_result] || 'Rut durumu güncellendi');
  };

  const pendingItems = useMemo(
    () => routeItems.filter((item) => item.status === 'pending'),
    [routeItems]
  );
  const visitedItems = useMemo(
    () => routeItems.filter((item) => item.status === 'visited'),
    [routeItems]
  );
  const subtitle = `${formatRouteDateLabel()} - ${routeItems.length} nokta`;

  return (
    <div className="mx-auto max-w-5xl space-y-6" data-testid="rut-page">
      <section
        className="rounded-[30px] border border-slate-200 bg-white px-6 py-6 shadow-[0_20px_60px_-35px_rgba(15,23,42,0.4)] md:px-8"
        data-testid="route-page-header-card"
      >
        <div className="space-y-5">
          <div>
            <h1 className="text-4xl font-bold tracking-tight text-slate-900" data-testid="route-page-title">
              Bugünün Noktaları
            </h1>
            <p className="mt-2 flex items-center gap-2 text-base text-slate-500" data-testid="route-page-subtitle">
              <CalendarDays className="h-4 w-4 text-slate-400" />
              {subtitle}
            </p>
          </div>

          <RouteSummaryBar
            pendingCount={pendingItems.length}
            visitedCount={visitedItems.length}
            totalPoints={routeItems.length}
          />
        </div>
      </section>

      {loading ? (
        <div className="rounded-[26px] border border-slate-200 bg-white px-6 py-10 shadow-[0_18px_45px_-30px_rgba(15,23,42,0.35)]" data-testid="route-loading-state">
          <Loading />
        </div>
      ) : (
        <div className="space-y-6">
          <RouteSection
            title="Bekleyen Noktalar"
            status="pending"
            items={pendingItems}
            onOpen={handlePendingItemOpen}
          />
          <RouteSection
            title="Gidilmiş Noktalar"
            status="visited"
            items={visitedItems}
            onOpen={handleVisitedItemOpen}
          />
        </div>
      )}

      <RouteActionModal
        isOpen={Boolean(selectedActionItem)}
        item={selectedActionItem}
        onClose={() => setSelectedActionItem(null)}
        onConfirm={handleActionConfirm}
        onOpenLocation={openLocation}
        onOpenMessages={openMessages}
        onOpenInvoice={openInvoice}
      />
      <RouteDetailDrawer item={selectedRouteItem} onClose={() => setSelectedRouteItem(null)} routeDay={routeDay} />
    </div>
  );
};

export default RutPage;
