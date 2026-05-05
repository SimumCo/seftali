// Plasiyer - Akıllı Sipariş Sayfası (UI Redesign)
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { sfSalesAPI } from '../../services/seftaliApi';
import { toast } from 'sonner';
import {
  AlertCircle,
  Box,
  Calendar,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  CupSoda,
  Package,
  Send,
  TriangleAlert,
  Users,
  Wallet,
} from 'lucide-react';

const DAYS = [
  { code: 'MON', label: 'Pazartesi' },
  { code: 'TUE', label: 'Salı' },
  { code: 'WED', label: 'Çarşamba' },
  { code: 'THU', label: 'Perşembe' },
  { code: 'FRI', label: 'Cuma' },
  { code: 'SAT', label: 'Cumartesi' },
  { code: 'SUN', label: 'Pazar' },
];

const getTomorrowDayCode = () => {
  const days = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return days[tomorrow.getDay()];
};

const formatAmount = (value) => Number(value || 0).toLocaleString('tr-TR');

const formatBalanceLabel = (data) => {
  const rawBalance = data?.balance ?? data?.available_balance ?? data?.remaining_balance ?? data?.bakiye;

  if (typeof rawBalance === 'number') {
    return `${new Intl.NumberFormat('en-US', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(rawBalance)} TL`;
  }

  if (typeof rawBalance === 'string' && rawBalance.trim()) {
    return rawBalance.includes('TL') ? rawBalance : `${rawBalance} TL`;
  }

  return '12,450.00 TL';
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';

  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString('tr-TR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return dateStr;
  }
};

const formatDebugRate = (value) => (value === null || value === undefined ? 'Veri yok' : `${Number(value).toLocaleString('tr-TR', { maximumFractionDigits: 2 })}/gün`);
const formatConfidence = (value) => (value === null || value === undefined ? 'Yetersiz veri' : `%${Math.round(Number(value) * 100)}`);
const formatTrend = (value) => {
  if (value === 'up') return '↑ Artıyor';
  if (value === 'down') return '↓ Düşüyor';
  if (value === 'stable') return '→ Stabil';
  return 'Hesaplanamadı';
};
const formatDebugValue = (value, fallback = 'Veri yok') => {
  if (value === null || value === undefined || value === '') return fallback;
  if (typeof value === 'number') return Number(value).toLocaleString('tr-TR', { maximumFractionDigits: 2 });
  return value;
};

const normalizeSmartDraftResponse = (draftData, fallbackRouteDay) => {
  if (!draftData?.customers) {
    return draftData;
  }

  const orderItems = (draftData.order_items || []).map((item) => ({
    ...item,
    final_qty: item.final_need_qty ?? item.need_qty ?? item.final_qty ?? 0,
  }));

  return {
    ...draftData,
    route_day: draftData.route_day || fallbackRouteDay,
    route_day_label: draftData.route_day_label || 'Müşteri Bazlı Draft',
    order_items: orderItems,
    excluded_items: draftData.excluded_items || [],
  };
};

const SummaryCard = ({ title, value, tone, testId }) => (
  <div
    className={`relative overflow-hidden rounded-[26px] p-6 text-white shadow-[0_20px_45px_-28px_rgba(15,23,42,0.45)] transition-transform duration-200 hover:-translate-y-0.5 ${tone}`}
    data-testid={testId}
  >
    <p className="text-sm font-medium tracking-wide text-white/80">{title}</p>
    <p className="mt-5 text-5xl font-bold leading-none">{value}</p>
  </div>
);

const QuantityDropdown = ({ item, onUpdateQty }) => {
  const [isOpen, setIsOpen] = useState(false);

  const options = useMemo(() => {
    const baseQty = item.edited_qty || 0;
    const step = item.box_size || 20;
    const list = [];

    for (let qty = 0; qty <= Math.max(baseQty * 2, step * 10); qty += step) {
      list.push(qty);
    }

    return list;
  }, [item.box_size, item.edited_qty]);

  return (
    <div className="relative w-full md:w-auto" data-testid={`qty-dropdown-wrapper-${item.product_id}`}>
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="flex h-12 w-full items-center justify-between rounded-2xl border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-900 shadow-sm transition-colors hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-orange-500 md:w-32"
        data-testid={`qty-dropdown-${item.product_id}`}
      >
        <span>{formatAmount(item.edited_qty || 0)}</span>
        <ChevronDown className={`h-4 w-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 z-20 mt-2 max-h-56 w-full overflow-y-auto rounded-2xl border border-slate-200 bg-white p-1 shadow-xl md:w-32">
          {options.map((qty) => (
            <button
              key={qty}
              type="button"
              onClick={() => {
                onUpdateQty(qty);
                setIsOpen(false);
              }}
              className={`w-full rounded-xl px-3 py-2 text-left text-sm transition-colors ${
                qty === item.edited_qty ? 'bg-orange-50 font-semibold text-orange-600' : 'text-slate-700 hover:bg-slate-50'
              }`}
              data-testid={`qty-option-${item.product_id}-${qty}`}
            >
              {formatAmount(qty)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

const ProductCard = ({ item, onUpdateQty, debugContext }) => {
  const [isDebugOpen, setIsDebugOpen] = useState(false);
  const plasiyerStock = item.plasiyer_stock || 0;
  const totalNeed = (item.order_qty || 0) + (item.draft_qty || 0);
  const boxSize = item.box_size || 20;
  const totalCases = boxSize > 1 ? Math.ceil(totalNeed / boxSize) : totalNeed;
  const stockClasses = plasiyerStock > 0 ? 'text-emerald-600 bg-emerald-50' : 'text-red-600 bg-red-50';
  const finalNeedQty = item.final_need_qty ?? item.final_qty ?? item.edited_qty ?? 0;
  const preClampNeedQty = item.pre_clamp_need_qty ?? item.need_qty ?? item.final_qty ?? 0;
  const trendLabel = formatTrend(item.trend);

  return (
    <div
      className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.4)] transition-shadow duration-200 hover:shadow-[0_18px_45px_-28px_rgba(15,23,42,0.45)]"
      data-testid={`warehouse-product-card-${item.product_id}`}
    >
      <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex min-w-0 flex-1 items-start gap-4">
          <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl border border-slate-100 bg-slate-50">
            <CupSoda className="h-6 w-6 text-slate-400" />
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="truncate text-xl font-bold text-slate-900">{item.product_name}</h3>
                <div className="mt-3 flex flex-col gap-2 text-sm text-slate-500 sm:flex-row sm:flex-wrap sm:items-center sm:gap-x-6">
                  <div className="flex items-center gap-2">
                    <Box className="h-4 w-4 text-slate-400" />
                    <span>
                      Depo stoğu: <span className="font-semibold text-blue-600">{formatAmount(item.warehouse_stock || 0)} ad</span>
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-slate-400" />
                    <span>
                      SKT: <span className="font-semibold text-slate-700">{formatDate(item.warehouse_skt)}</span>
                    </span>
                  </div>
                </div>
              </div>
              <div className="rounded-2xl bg-slate-50 px-4 py-3 text-right" data-testid={`warehouse-product-mini-summary-${item.product_id}`}>
                <p className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-400">Hızlı Bakış</p>
                <div className="mt-2 space-y-1 text-sm">
                  <p><span className="text-slate-500">Günlük tüketim:</span> <span className="font-semibold text-slate-900">{formatDebugRate(item.rate_mt_weighted ?? item.rate_mt)}</span></p>
                  <p><span className="text-slate-500">Trend:</span> <span className="font-semibold text-slate-900">{trendLabel}</span></p>
                  <p><span className="text-slate-500">Son öneri:</span> <span className="font-semibold text-orange-600">{formatAmount(finalNeedQty)} ad</span></p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid w-full gap-4 lg:grid-cols-[minmax(120px,auto)_minmax(220px,auto)_minmax(150px,auto)] xl:w-auto xl:items-center">
          <div className="text-left lg:text-right">
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">stok</p>
            <span className={`mt-2 inline-flex rounded-full px-3 py-1 text-sm font-bold ${stockClasses}`} data-testid={`product-stock-${item.product_id}`}>
              {formatAmount(plasiyerStock)} ad
            </span>
          </div>

          <div className="text-left lg:text-right">
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">taslak ve sipariş toplam</p>
            <div className="mt-2 flex flex-wrap items-center gap-2 lg:justify-end">
              <span className="text-sm font-semibold text-slate-800">{formatAmount(totalNeed)} ad</span>
              <span className="rounded-full bg-orange-50 px-3 py-1 text-xs font-bold text-orange-600">
                {totalCases} koli
              </span>
            </div>
          </div>

          <div className="w-full lg:justify-self-end">
            <p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-slate-400 lg:text-right">tahmini ihtiyaç</p>
            <QuantityDropdown item={item} onUpdateQty={onUpdateQty} />
          </div>
        </div>
      </div>

      <div className="mt-5 border-t border-slate-100 pt-4">
        <button
          type="button"
          onClick={() => setIsDebugOpen((value) => !value)}
          className="flex items-center gap-2 text-sm font-semibold text-slate-700 transition-colors hover:text-orange-600"
          data-testid={`warehouse-product-debug-toggle-${item.product_id}`}
        >
          <ChevronRight className={`h-4 w-4 transition-transform ${isDebugOpen ? 'rotate-90' : ''}`} />
          {isDebugOpen ? 'Detayları Gizle' : 'Detayları Gör'}
        </button>

        {isDebugOpen && (
          <div className="mt-4 grid gap-4 lg:grid-cols-2" data-testid={`warehouse-product-debug-panel-${item.product_id}`}>
            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Tüketim</p>
              <div className="mt-3 space-y-2 text-sm">
                <p><span className="text-slate-500">Günlük tüketim:</span> <span className="font-semibold text-slate-900">{formatDebugRate(item.rate_mt_weighted ?? item.rate_mt)}</span></p>
                <p><span className="text-slate-500">Kaynak:</span> <span className="font-semibold text-slate-900">{item.rate_source || 'Veri yok'}</span></p>
                <p><span className="text-slate-500">Güven:</span> <span className="font-semibold text-slate-900">{formatConfidence(item.confidence_score)}</span></p>
                <p><span className="text-slate-500">Trend:</span> <span className="font-semibold text-slate-900">{trendLabel}</span></p>
              </div>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Rota</p>
              <div className="mt-3 space-y-2 text-sm">
                <p><span className="text-slate-500">Son teslimat:</span> <span className="font-semibold text-slate-900">{formatDate(item.last_delivery_date)}</span></p>
                <p><span className="text-slate-500">Bugün:</span> <span className="font-semibold text-slate-900">{formatDate(debugContext.todayDate)}</span></p>
                <p><span className="text-slate-500">Sonraki rota:</span> <span className="font-semibold text-slate-900">{formatDate(debugContext.nextRouteDate)}</span></p>
                <p><span className="text-slate-500">Gün farkı:</span> <span className="font-semibold text-slate-900">{formatDebugValue(item.days_to_next_route ?? debugContext.daysToNextRoute, 'Veri yok')}</span></p>
              </div>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Multiplier</p>
              <div className="mt-3 space-y-2 text-sm">
                <p><span className="text-slate-500">Weekly multiplier:</span> <span className="font-semibold text-slate-900">{formatDebugValue(item.weekly_multiplier, 'Veri yok')}</span></p>
                <p><span className="text-slate-500">Kaynak:</span> <span className="font-semibold text-slate-900">{item.weekly_multiplier_source || 'Veri yok'}</span></p>
              </div>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Hesap</p>
              <div className="mt-3 space-y-2 text-sm">
                <p><span className="text-slate-500">Ham ihtiyaç:</span> <span className="font-semibold text-slate-900">{formatDebugValue(preClampNeedQty, 'Veri yok')}</span></p>
                <p><span className="text-slate-500">Son ihtiyaç:</span> <span className="font-semibold text-orange-600">{formatDebugValue(finalNeedQty, 'Veri yok')}</span></p>
                {item.was_clamped && (
                  <div className="inline-flex items-center gap-2 rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700" data-testid={`warehouse-product-clamp-flag-${item.product_id}`}>
                    <TriangleAlert className="h-3.5 w-3.5" />
                    SKT nedeniyle düşürüldü
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-2xl bg-slate-50 p-4 lg:col-span-2">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">SKT</p>
              <div className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-5">
                <p><span className="text-slate-500">Raf ömrü:</span> <span className="font-semibold text-slate-900">{formatDebugValue(item.shelf_life_days, 'Veri yok')}</span></p>
                <p><span className="text-slate-500">Coverage:</span> <span className="font-semibold text-slate-900">{formatDebugValue(item.coverage_days, 'Veri yok')}</span></p>
                <p><span className="text-slate-500">Clamp:</span> <span className="font-semibold text-slate-900">{item.was_clamped ? 'Evet' : 'Hayır'}</span></p>
                <p><span className="text-slate-500">Max safe qty:</span> <span className="font-semibold text-slate-900">{formatDebugValue(item.max_safe_qty, 'Veri yok')}</span></p>
                <p><span className="text-slate-500">Not:</span> <span className="font-semibold text-slate-900">{item.clamp_reason || 'Veri yok'}</span></p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

const WarehouseDraftPage = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [selectedDay] = useState(getTomorrowDayCode());
  const [orderItems, setOrderItems] = useState([]);
  const [showExcludedItems, setShowExcludedItems] = useState(false);

  const fetchDraft = useCallback(async () => {
    try {
      setLoading(true);
      let draftData = null;
      try {
        const res = await sfSalesAPI.getSmartDraftV2();
        draftData = normalizeSmartDraftResponse(res.data?.data || null, selectedDay);
      } catch (smartDraftError) {
        console.warn('smart-draft-v2 failed, falling back to warehouse-draft', smartDraftError);
        const res = await sfSalesAPI.getWarehouseDraft();
        draftData = res.data?.data || null;
      }

      setData(draftData);

      if (draftData?.order_items) {
        setOrderItems(
          draftData.order_items.map((item) => ({
            ...item,
            edited_qty: item.final_need_qty ?? item.final_qty,
            is_edited: false,
          }))
        );
      } else {
        setOrderItems([]);
      }
    } catch {
      toast.error('Depo taslağı yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, [selectedDay]);

  useEffect(() => {
    fetchDraft();
  }, [fetchDraft]);

  const updateItemQty = (productId, newQty) => {
    setOrderItems((items) =>
      items.map((item) => {
        if (item.product_id !== productId) {
          return item;
        }

        const boxSize = item.box_size || 1;
        const roundedQty = boxSize > 1 ? Math.ceil(newQty / boxSize) * boxSize : Math.max(0, newQty);

        return {
          ...item,
          edited_qty: roundedQty,
          is_edited: roundedQty !== item.final_qty,
        };
      })
    );
  };

  const handleSubmit = async () => {
    const activeItems = orderItems.filter((item) => item.edited_qty > 0);

    if (activeItems.length === 0) {
      toast.error('Sipariş listesi boş');
      return;
    }

    try {
      setSubmitting(true);
      await sfSalesAPI.submitWarehouseDraft({
        items: activeItems.map((item) => ({
          product_id: item.product_id,
          qty: item.edited_qty,
        })),
        route_day: selectedDay,
        note: '',
      });
      toast.success('Depo siparişi başarıyla gönderildi!');
      fetchDraft();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gönderim hatası');
    } finally {
      setSubmitting(false);
    }
  };

  const timeInfo = useMemo(() => {
    const now = new Date();
    const cutoff = new Date(now);
    cutoff.setHours(16, 30, 0, 0);
    return { isAfterCutoff: now > cutoff };
  }, []);

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-orange-500" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex h-64 flex-col items-center justify-center rounded-[28px] border border-slate-200 bg-white text-slate-500 shadow-sm">
        <Package className="mb-4 h-12 w-12 opacity-40" />
        <p>Veri yüklenemedi</p>
      </div>
    );
  }

  const routeDayLabel = DAYS.find((day) => day.code === data.route_day)?.label || data.route_day;
  const balanceLabel = formatBalanceLabel(data);
  const debugContext = {
    todayDate: data?.calculation_params?.today_date,
    nextRouteDate: data?.route_info?.next_route_date,
    daysToNextRoute: data?.route_info?.days_to_next_route,
  };
  const excludedItems = data?.excluded_items || [];

  return (
    <div className="space-y-8" data-testid="akilli-siparis-page">
      <section className="rounded-[30px] border border-slate-200 bg-white p-6 shadow-[0_22px_60px_-38px_rgba(15,23,42,0.5)] lg:p-8">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
          <div>
            <div className="flex flex-col gap-2 xl:flex-row xl:items-center xl:gap-4">
              <h1 className="text-4xl font-bold tracking-tight text-slate-900" data-testid="warehouse-draft-title">
                Depo Sipariş Oluştur
              </h1>
              <p className="text-lg text-slate-500" data-testid="warehouse-draft-subtitle">
                {routeDayLabel} rutu için sipariş taslağı
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-3 xl:items-end">
            <div
              className="inline-flex items-center gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-800 shadow-sm"
              data-testid="warehouse-balance-badge"
            >
              <Wallet className="h-5 w-5 text-amber-600" />
              <span className="text-sm font-semibold">Bakiye: {balanceLabel}</span>
            </div>

            {timeInfo.isAfterCutoff && (
              <div className="flex max-w-xl items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700" data-testid="warehouse-cutoff-alert">
                <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-amber-500" />
                <div>
                  <p className="font-semibold">Sipariş kesim saati geçti!</p>
                  <p className="mt-1 text-amber-600">16:30'dan sonra gelen siparişler bir sonraki planlamaya dahil edilir.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-3" data-testid="warehouse-summary-cards">
        <SummaryCard title="Rut Müşterisi" value={data.customer_count || 0} tone="bg-gradient-to-br from-blue-500 to-blue-600" testId="warehouse-summary-route-customers" />
        <SummaryCard title="Sipariş Veren" value={data.order_customer_count || 0} tone="bg-gradient-to-br from-emerald-500 to-emerald-600" testId="warehouse-summary-order-customers" />
        <SummaryCard title="Taslakta" value={data.draft_customer_count || 0} tone="bg-gradient-to-br from-orange-500 to-orange-600" testId="warehouse-summary-draft-customers" />
      </section>

      <section className="space-y-5">
        <div className="flex flex-wrap items-center gap-3 text-slate-900">
          <Users className="h-6 w-6 text-slate-500" />
          <h2 className="text-2xl font-bold tracking-tight">Müşteri Siparişleri & Taslaklar</h2>
          {excludedItems.length > 0 && (
            <button
              type="button"
              onClick={() => setShowExcludedItems((value) => !value)}
              className="inline-flex items-center gap-2 rounded-full border border-red-200 bg-red-50 px-3 py-1 text-sm font-semibold text-red-700"
              data-testid="warehouse-excluded-items-toggle"
            >
              <TriangleAlert className="h-4 w-4" />
              {excludedItems.length} ürün önerilmedi
            </button>
          )}
        </div>

        {showExcludedItems && excludedItems.length > 0 && (
          <div className="rounded-[24px] border border-red-200 bg-red-50 p-4" data-testid="warehouse-excluded-items-panel">
            <p className="text-sm font-semibold text-red-800">Önerilmeyen Ürünler</p>
            <div className="mt-3 space-y-2">
              {excludedItems.map((item) => (
                <div key={item.product_id} className="rounded-2xl bg-white/80 px-4 py-3 text-sm text-red-700">
                  <p className="font-semibold text-slate-900">{item.product_name}</p>
                  <p className="mt-1">{item.abandoned_reason || 'Bu ürün için öneri oluşturulmadı'}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4" data-testid="warehouse-product-list">
          {orderItems.length > 0 ? (
            orderItems.map((item) => (
              <ProductCard key={item.product_id} item={item} onUpdateQty={(qty) => updateItemQty(item.product_id, qty)} debugContext={debugContext} />
            ))
          ) : (
            <div className="rounded-[28px] border border-slate-200 bg-white px-6 py-14 text-center text-slate-500 shadow-sm" data-testid="warehouse-empty-state">
              <Package className="mx-auto mb-4 h-12 w-12 opacity-30" />
              <p className="text-base font-medium">Bu rota için henüz ürün taslağı oluşmadı</p>
              <p className="mt-2 text-sm text-slate-400">Sipariş veya taslak oluştuğunda ürün kartları bu alanda listelenecek.</p>
            </div>
          )}
        </div>
      </section>

      <section className="space-y-4">
        {orderItems.length > 0 && (
          <button
            onClick={handleSubmit}
            disabled={submitting}
            className={`flex w-full items-center justify-center gap-2 rounded-[22px] py-4 text-base font-bold text-white transition-all ${
              submitting
                ? 'cursor-not-allowed bg-slate-300'
                : 'bg-gradient-to-r from-orange-500 to-orange-600 shadow-[0_18px_40px_-25px_rgba(249,115,22,0.65)] hover:from-orange-600 hover:to-orange-700'
            }`}
            data-testid="submit-warehouse-btn"
          >
            <Send className="h-5 w-5" />
            {submitting ? 'Gönderiliyor...' : 'Depoya Sipariş Gönder'}
          </button>
        )}

        <div className="rounded-[24px] border border-blue-100 bg-blue-50 px-5 py-4" data-testid="warehouse-info-box">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 h-5 w-5 flex-shrink-0 text-blue-500" />
            <div className="text-sm text-blue-700">
              <p className="font-semibold text-blue-900">Nasıl çalışır?</p>
              <ul className="mt-2 space-y-1 text-blue-700">
                <li>Müşteri siparişleri ve sistem taslakları birlikte değerlendirilir.</li>
                <li>Plasiyer stoğu ihtiyaç hesabından otomatik düşülür.</li>
                <li>Koli bilgisi öne çıkarılır; tahmini ihtiyaç alanı geçici olarak düzenlenebilir.</li>
              </ul>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default WarehouseDraftPage;
