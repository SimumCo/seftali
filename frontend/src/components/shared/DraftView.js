import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { sfCustomerAPI } from '../../services/seftaliApi';
import {
  AlertTriangle,
  CalendarDays,
  ChevronRight,
  CupSoda,
  Minus,
  Package,
  Search,
  Send,
  ShoppingCart,
  Snowflake,
  Plus,
} from 'lucide-react';
import { toast } from 'sonner';

const DAY_TR = {
  MON: 'Pazartesi',
  TUE: 'Salı',
  WED: 'Çarşamba',
  THU: 'Perşembe',
  FRI: 'Cuma',
  SAT: 'Cumartesi',
  SUN: 'Pazar',
};

const DAY_NUM = { MON: 1, TUE: 2, WED: 3, THU: 4, FRI: 5, SAT: 6, SUN: 0 };

function getNextRouteInfo(routeDays) {
  if (!routeDays?.length) {
    return { label: null, routeDate: null, deadline: null, diff: null, nextDayLabel: null };
  }

  const now = new Date();
  let minDiff = 8;
  let nextDayCode = null;

  for (const day of routeDays) {
    const target = DAY_NUM[day] ?? 0;
    let diff = (target - now.getDay() + 7) % 7;
    if (diff === 0) diff = 7;
    if (diff < minDiff) {
      minDiff = diff;
      nextDayCode = day;
    }
  }

  const routeDate = new Date(now.getTime() + minDiff * 86400000);
  routeDate.setHours(0, 0, 0, 0);

  const deadline = new Date(routeDate.getTime() - 86400000);
  deadline.setHours(16, 0, 0, 0);
  const deadlineLate = new Date(deadline.getTime() + 30 * 60000);

  return {
    label: routeDays.map((day) => DAY_TR[day] || day).join(', '),
    routeDate,
    deadline: now > deadlineLate ? null : deadline,
    deadlineLate,
    diff: minDiff,
    nextDayLabel: DAY_TR[nextDayCode] || nextDayCode,
  };
}

function useCountdown(deadline) {
  const [remaining, setRemaining] = useState('');
  const [isUrgent, setIsUrgent] = useState(false);
  const [isExpired, setIsExpired] = useState(false);

  useEffect(() => {
    if (!deadline) {
      setRemaining('');
      setIsUrgent(false);
      setIsExpired(false);
      return undefined;
    }

    const tick = () => {
      const diff = deadline.getTime() - Date.now();
      if (diff <= 0) {
        const toleranceMs = 30 * 60000;
        if (diff > -toleranceMs) {
          setRemaining('Son 30 dakika');
          setIsUrgent(true);
          setIsExpired(false);
        } else {
          setRemaining('Süre doldu');
          setIsExpired(true);
          setIsUrgent(false);
        }
        return;
      }

      const dayCount = Math.floor(diff / 86400000);
      const hourCount = Math.floor((diff % 86400000) / 3600000);
      const minuteCount = Math.floor((diff % 3600000) / 60000);
      setIsUrgent(diff < 4 * 3600000);
      setIsExpired(false);
      setRemaining(
        dayCount > 0
          ? `${dayCount} gün ${hourCount.toString().padStart(2, '0')}:${minuteCount.toString().padStart(2, '0')}`
          : `${hourCount.toString().padStart(2, '0')}:${minuteCount.toString().padStart(2, '0')}`
      );
    };

    tick();
    const interval = setInterval(tick, 60000);
    return () => clearInterval(interval);
  }, [deadline]);

  return { remaining, isUrgent, isExpired };
}

const formatQty = (value) => {
  if (value === null || value === undefined || value === '') return '';
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return String(value);
  return Number.isInteger(numeric) ? String(numeric) : numeric.toLocaleString('tr-TR', { maximumFractionDigits: 2 });
};

const getUnitLabel = (product) => {
  const unitType = (product.unit_type || '').toLowerCase();
  if (unitType.includes('bottle')) return 'Birim: Şişe';
  if (unitType.includes('unit')) return 'Birim: Adet';
  if (unitType.includes('adet')) return 'Birim: Adet';
  return product.case_size ? `Koli içi: ${product.case_size}` : 'Birim: Adet';
};

const getProductVisualTone = (name = '') => {
  const normalized = name.toLowerCase();
  if (normalized.includes('ayran')) {
    return 'bg-sky-50 text-sky-600 border-sky-100';
  }
  if (normalized.includes('yoğurt') || normalized.includes('yogurt')) {
    return 'bg-amber-50 text-amber-600 border-amber-100';
  }
  return 'bg-slate-50 text-slate-500 border-slate-100';
};

const QuantityInput = ({ product, value, onChange }) => {
  const numericValue = value === '' ? '' : Number(value) || 0;

  const updateValue = (nextValue) => {
    if (nextValue <= 0) {
      onChange('');
      return;
    }
    onChange(String(nextValue));
  };

  return (
    <div className="flex items-center rounded-[20px] border border-slate-200 bg-white shadow-sm" data-testid={`customer-qty-stepper-${product.product_id}`}>
      <button
        type="button"
        onClick={() => updateValue((Number(numericValue) || 0) - 1)}
        className="flex h-12 w-12 items-center justify-center rounded-l-[20px] text-slate-500 transition-colors hover:bg-slate-50"
        data-testid={`customer-qty-minus-${product.product_id}`}
        aria-label={`${product.product_name} miktar azalt`}
      >
        <Minus className="h-4 w-4" />
      </button>

      <input
        type="number"
        min="0"
        inputMode="numeric"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={product.suggested_qty > 0 ? formatQty(product.suggested_qty) : '0'}
        className="h-12 w-full min-w-[88px] border-x border-slate-200 bg-transparent px-3 text-center text-base font-semibold text-slate-900 outline-none placeholder:font-medium placeholder:text-orange-400 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        data-testid={`customer-qty-input-${product.product_id}`}
        aria-label={`${product.product_name} miktar girişi`}
      />

      <button
        type="button"
        onClick={() => updateValue((Number(numericValue) || 0) + 1)}
        className="flex h-12 w-12 items-center justify-center rounded-r-[20px] text-slate-500 transition-colors hover:bg-slate-50"
        data-testid={`customer-qty-plus-${product.product_id}`}
        aria-label={`${product.product_name} miktar artır`}
      >
        <Plus className="h-4 w-4" />
      </button>
    </div>
  );
};

const ProductCard = ({ product, quantity, onQuantityChange }) => {
  const showSuggested = product.suggested_qty > 0;
  const numericQuantity = quantity === '' ? 0 : Number(quantity) || 0;
  const showOverOrderWarning = showSuggested && numericQuantity > product.suggested_qty * 2;
  const showFastSelling = (product.avg_daily || 0) > 5;
  const showSktWarning = Boolean(product.flags?.skt_risk);

  return (
    <article
      className="rounded-[28px] border border-slate-200 bg-white p-5 shadow-[0_16px_40px_-30px_rgba(15,23,42,0.4)] transition-transform transition-shadow duration-200 hover:-translate-y-0.5 hover:shadow-[0_18px_45px_-28px_rgba(15,23,42,0.45)]"
      data-testid={`customer-product-card-${product.product_id}`}
    >
      <div className="flex items-start gap-4">
        <div className={`flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-2xl border ${getProductVisualTone(product.product_name)}`}>
          <CupSoda className="h-6 w-6" />
        </div>

        <div className="min-w-0 flex-1 space-y-4">
          <div className="space-y-2">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="truncate text-xl font-bold tracking-tight text-slate-900">{product.product_name}</h3>
                <p className="mt-1 text-sm text-slate-500">{getUnitLabel(product)}</p>
              </div>

              {showSuggested && (
                <span className="inline-flex rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700" data-testid={`customer-badge-onerilen-${product.product_id}`}>
                  Önerilen: {formatQty(product.suggested_qty)}
                </span>
              )}
            </div>

            {showSuggested && (
              <p className="text-sm text-slate-500" data-testid={`customer-suggestion-copy-${product.product_id}`}>
                Son sipariş ve tüketim hızınıza göre önerildi
              </p>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            {showFastSelling && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700" data-testid={`customer-badge-dikkat-${product.product_id}`}>
                <AlertTriangle className="h-3.5 w-3.5" />
                Bu ürün hızlı tükeniyor
              </span>
            )}

            {showSktWarning && (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-3 py-1 text-xs font-medium text-red-700" data-testid={`customer-badge-skt-${product.product_id}`}>
                <Snowflake className="h-3.5 w-3.5" />
                SKT süresi kısa olabilir
              </span>
            )}

            {showOverOrderWarning && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-700" data-testid={`customer-badge-overorder-${product.product_id}`}>
                <AlertTriangle className="h-3.5 w-3.5" />
                Bu miktar ihtiyacınızdan fazla olabilir
              </span>
            )}
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div className="w-full sm:max-w-[220px]">
              <p className="mb-2 text-xs font-medium uppercase tracking-[0.2em] text-slate-400">Miktar</p>
              <QuantityInput product={product} value={quantity} onChange={onQuantityChange} />
            </div>

            <div className="text-sm text-slate-400">
              {numericQuantity > 0 ? `${formatQty(numericQuantity)} adet seçildi` : 'Miktarı manuel girin veya adım butonlarını kullanın'}
            </div>
          </div>
        </div>
      </div>
    </article>
  );
};

const DraftView = () => {
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState({});
  const [loading, setLoading] = useState(true);
  const [profile, setProfile] = useState(null);
  const [search, setSearch] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryRes, draftRes, profileRes, productsRes] = await Promise.all([
        sfCustomerAPI.getConsumptionSummary(),
        sfCustomerAPI.getDraft(),
        sfCustomerAPI.getProfile(),
        sfCustomerAPI.getProducts(),
      ]);

      const summary = summaryRes.data?.data || [];
      const draftItems = draftRes.data?.data?.items || [];
      const allProducts = productsRes.data?.data || [];
      setProfile(profileRes.data?.data || null);

      const summaryMap = Object.fromEntries(summary.map((item) => [item.product_id, item]));
      const draftMap = Object.fromEntries(draftItems.map((item) => [item.product_id, item]));
      const productMetaMap = Object.fromEntries(
        allProducts.map((item) => [item.product_id || item.id, item])
      );

      const ids = Array.from(new Set([...summary.map((item) => item.product_id), ...draftItems.map((item) => item.product_id)]));
      const merged = ids
        .map((productId) => {
          const summaryItem = summaryMap[productId] || {};
          const draftItem = draftMap[productId] || {};
          const productMeta = productMetaMap[productId] || {};

          return {
            product_id: productId,
            product_name: draftItem.product_name || summaryItem.product_name || productMeta.name || productId,
            suggested_qty: draftItem.suggested_qty || 0,
            avg_daily: summaryItem.avg_daily || 0,
            unit_type: productMeta.unit_type || 'adet',
            case_size: productMeta.case_size || 1,
            flags: draftItem.flags || {},
          };
        })
        .sort((a, b) => (b.suggested_qty || 0) - (a.suggested_qty || 0) || (b.avg_daily || 0) - (a.avg_daily || 0));

      setProducts(merged);
      setCart({});
    } catch {
      toast.error('Veriler yüklenemedi');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const routeDays = profile?.route_plan?.days || [];
  const fallbackRouteInfo = getNextRouteInfo(routeDays);
  const nextDeliveryDay = fallbackRouteInfo.nextDayLabel;
  const { remaining: countdown, isUrgent, isExpired } = useCountdown(fallbackRouteInfo.deadline);

  const filteredProducts = useMemo(() => {
    if (!search) return products;
    return products.filter((product) =>
      product.product_name?.toLowerCase().includes(search.toLowerCase())
    );
  }, [products, search]);

  const setCartQty = (product, rawValue) => {
    const numericValue = rawValue === '' ? '' : String(Math.max(0, parseInt(rawValue, 10) || 0));

    setCart((previous) => {
      const next = { ...previous };
      const qty = numericValue === '' ? 0 : Number(numericValue);

      if (qty <= 0) {
        delete next[product.product_id];
        return next;
      }

      next[product.product_id] = {
        product_id: product.product_id,
        product_name: product.product_name,
        quantity: qty,
      };
      return next;
    });
  };

  const cartItems = Object.values(cart);
  const totalSelectedTypes = cartItems.length;
  const totalQuantity = cartItems.reduce((sum, item) => sum + item.quantity, 0);

  const handleSubmitOrder = async () => {
    if (cartItems.length === 0 || totalQuantity === 0) {
      toast.error('En az 1 ürün için miktar girin');
      return;
    }

    try {
      setSubmitting(true);
      const workingCopyResponse = await sfCustomerAPI.startWorkingCopy();
      const workingCopyId = workingCopyResponse.data?.data?.id;

      if (!workingCopyId) {
        throw new Error('Çalışma kopyası oluşturulamadı');
      }

      await sfCustomerAPI.updateWorkingCopy(
        workingCopyId,
        cartItems.map((item) => ({
          product_id: item.product_id,
          user_qty: item.quantity,
          removed: false,
        }))
      );
      await sfCustomerAPI.submitWorkingCopy(workingCopyId);
      toast.success('Siparişiniz başarıyla gönderildi');
      setCart({});
      fetchData();
    } catch (err) {
      toast.error(`Sipariş gönderilemedi: ${err.response?.data?.detail || err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="h-10 w-10 animate-spin rounded-full border-b-2 border-orange-500" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6 pb-36" data-testid="draft-view">
      <section className="rounded-[30px] border border-slate-200 bg-white p-6 shadow-[0_20px_55px_-38px_rgba(15,23,42,0.45)] sm:p-7">
        <div className="space-y-4">
          <div className="space-y-2">
            <h1 className="text-4xl font-black tracking-tight text-slate-900" data-testid="customer-order-title">
              Sipariş Oluştur
            </h1>
            <p className="text-base text-slate-500" data-testid="customer-order-subtitle">
              Size özel önerilen ürünlerle hızlı sipariş verin
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <span className="inline-flex items-center gap-2 rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700" data-testid="customer-next-delivery-badge">
              <CalendarDays className="h-4 w-4 text-slate-500" />
              Teslimat: {nextDeliveryDay || '—'}
            </span>

            {countdown && (
              <span
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium ${
                  isExpired ? 'bg-red-50 text-red-700' : isUrgent ? 'bg-amber-50 text-amber-700' : 'bg-orange-50 text-orange-700'
                }`}
                data-testid="customer-order-countdown"
              >
                <AlertTriangle className="h-4 w-4" />
                {isExpired ? 'Sipariş süresi doldu' : `Kalan süre: ${countdown}`}
              </span>
            )}
          </div>

          <div className="relative">
            <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Ürün ara"
              className="h-12 w-full rounded-2xl border border-slate-200 bg-slate-50 pl-11 pr-4 text-sm text-slate-700 outline-none transition-colors focus:border-orange-300 focus:ring-2 focus:ring-orange-100"
              data-testid="customer-order-search-input"
            />
          </div>
        </div>
      </section>

      <section className="space-y-5" data-testid="customer-product-list">
        {filteredProducts.length > 0 ? (
          filteredProducts.map((product) => (
            <ProductCard
              key={product.product_id}
              product={product}
              quantity={cart[product.product_id]?.quantity ?? ''}
              onQuantityChange={(value) => setCartQty(product, value)}
            />
          ))
        ) : (
          <div className="rounded-[28px] border border-slate-200 bg-white px-6 py-16 text-center text-slate-500 shadow-sm" data-testid="customer-order-empty-state">
            <Package className="mx-auto mb-4 h-12 w-12 opacity-30" />
            <p className="text-base font-medium">Gösterilecek ürün bulunamadı</p>
            <p className="mt-2 text-sm text-slate-400">Arama filtresini temizleyip tekrar deneyin.</p>
          </div>
        )}
      </section>

      <div
        className="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-200 bg-white/85 px-4 py-4 backdrop-blur-xl lg:left-56"
        data-testid="customer-order-bottom-bar"
      >
        <div className="mx-auto flex max-w-4xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3 rounded-[22px] bg-slate-100 px-4 py-3 text-slate-700">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-orange-500 shadow-sm">
              <ShoppingCart className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-400">Sipariş Özeti</p>
              <p className="mt-1 text-sm font-semibold text-slate-800" data-testid="customer-order-summary-text">
                {totalSelectedTypes} ürün • {formatQty(totalQuantity)} adet
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleSubmitOrder}
            disabled={submitting || totalQuantity === 0 || isExpired}
            className={`flex items-center justify-center gap-2 rounded-[22px] px-5 py-4 text-base font-bold text-white transition-colors duration-200 ${
              submitting || totalQuantity === 0 || isExpired
                ? 'cursor-not-allowed bg-slate-300'
                : 'bg-orange-500 shadow-[0_18px_40px_-28px_rgba(249,115,22,0.7)] hover:bg-orange-600'
            }`}
            data-testid="customer-review-order-button"
          >
            <Send className="h-5 w-5" />
            {submitting ? 'Gönderiliyor...' : isExpired ? 'Süre Doldu' : 'Siparişi Gözden Geçir'}
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default DraftView;
