import React, { useEffect, useMemo, useState } from 'react';
import { CalendarDays, CheckCircle2, CloudOff, FileText, KeyRound, Loader2, PlugZap, Plus, RefreshCcw, ShieldAlert, Trash2, Unplug } from 'lucide-react';
import { toast } from 'sonner';

import gibApi from '../services/gibApi';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';

const RANGE_OPTIONS = [
  { value: 'last_7', label: 'Son 7 gün', days: 7 },
  { value: 'last_30', label: 'Son 30 gün', days: 30 },
  { value: 'last_90', label: 'Son 90 gün', days: 90 },
  { value: 'custom', label: 'Özel aralık', days: null },
];

const statusMeta = {
  connected: { label: 'Bağlı', className: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  not_connected: { label: 'Bağlı değil', className: 'bg-slate-100 text-slate-600 border-slate-200' },
  expired: { label: 'Süresi dolmuş', className: 'bg-amber-50 text-amber-700 border-amber-200' },
};

const mapErrorMessage = (error) => {
  const detail = error?.response?.data?.detail;
  const code = typeof detail === 'object' ? detail?.code : detail;
  switch (code) {
    case 'invalid_credentials':
      return 'Kullanıcı kodu veya şifre hatalı.';
    case 'captcha_required':
      return 'GİB doğrulama istiyor. Tekrar deneyin.';
    case 'otp_required':
      return 'Ek doğrulama gerekiyor.';
    case 'session_expired':
      return 'Oturum süresi doldu. Yeniden bağlanın.';
    case 'portal_layout_changed':
      return 'GİB yapısı değişmiş olabilir. Teknik kontrol gerekiyor.';
    case 'gib_temporarily_unavailable':
      return 'GİB şu an erişilemiyor. Daha sonra tekrar deneyin.';
    case 'not_connected':
      return 'Önce GİB bağlantısı kurun.';
    case 'provider_config_missing':
      return 'Servis yapılandırması eksik. Yönetici ile iletişime geçin.';
    case 'VALIDATION_ERROR':
      return 'Fatura bilgilerinde hata var. Lütfen kontrol edin.';
    default:
      if (error?.response?.status === 422) {
        return 'Gönderilen bilgilerde doğrulama hatası var.';
      }
      if (error?.response?.status === 504) {
        return 'Servis zaman aşımına uğradı. Lütfen tekrar deneyin.';
      }
      if (error?.response?.status === 503) {
        return 'Servise ulaşılamıyor. Daha sonra tekrar deneyin.';
      }
      if (error?.response?.status === 401 || error?.response?.status === 403) {
        return 'Yetkilendirme hatası. Lütfen yöneticinize bildirin.';
      }
      return detail?.message || detail?.provider_message || detail || error?.message || 'İşlem tamamlanamadı.';
  }
};

const extractValidationHints = (error) => {
  const detail = error?.response?.data?.detail;
  if (detail && typeof detail === 'object' && Array.isArray(detail.validation_hints)) {
    return detail.validation_hints;
  }
  return [];
};

const getDateRange = (rangeType, customFrom, customTo) => {
  const today = new Date();
  const to = today.toISOString().slice(0, 10);
  if (rangeType === 'custom') {
    return { date_from: customFrom, date_to: customTo };
  }

  const option = RANGE_OPTIONS.find((item) => item.value === rangeType);
  const days = option?.days || 30;
  const fromDate = new Date(today);
  fromDate.setDate(today.getDate() - days);
  return {
    date_from: fromDate.toISOString().slice(0, 10),
    date_to: to,
  };
};

const formatDateTime = (value) => {
  if (!value) return '—';
  try {
    return new Date(value).toLocaleString('tr-TR');
  } catch {
    return value;
  }
};

export default function GibConnectionPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [statusData, setStatusData] = useState({ state: 'not_connected' });
  const [selectedRange, setSelectedRange] = useState('last_30');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');
  const [importSummary, setImportSummary] = useState(null);
  const [loading, setLoading] = useState({ connect: false, status: false, import: false, disconnect: false, initial: true, outbox: false });

  // --- Outbox Create form state (Turkcell v1 /outboxinvoice/create) ---
  const todayISO = new Date().toISOString().slice(0, 10);
  const generateLocalRef = () => `INV-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}`;
  const [outboxForm, setOutboxForm] = useState({
    local_reference_id: generateLocalRef(),
    issue_date: todayISO,
    receiver_vkn: '',
    receiver_title: '',
    receiver_alias: '',
    receiver_tax_office: '',
    receiver_city: '',
    receiver_district: '',
    receiver_street: '',
    receiver_postal_code: '',
  });
  const [outboxLines, setOutboxLines] = useState([
    { name: '', quantity: '1', unit_price: '0.00', vat_rate: '10' },
  ]);
  const [outboxResult, setOutboxResult] = useState(null);
  const [outboxHints, setOutboxHints] = useState([]);

  const currentStatus = statusMeta[statusData?.state] || statusMeta.not_connected;
  const importDisabled = statusData?.state !== 'connected' || loading.import || loading.connect;

  const activeRange = useMemo(() => getDateRange(selectedRange, customFrom, customTo), [selectedRange, customFrom, customTo]);

  const loadStatus = async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading((prev) => ({ ...prev, status: true }));
    }
    try {
      const response = await gibApi.status();
      setStatusData(response.data?.data || { state: 'not_connected' });
    } catch (error) {
      if (!silent) {
        toast.error(mapErrorMessage(error));
      }
      setStatusData({ state: 'not_connected' });
    } finally {
      setLoading((prev) => ({ ...prev, status: false, initial: false }));
    }
  };

  useEffect(() => {
    loadStatus({ silent: true });
  }, []);

  const handleConnect = async (event) => {
    event.preventDefault();
    setLoading((prev) => ({ ...prev, connect: true }));
    try {
      const response = await gibApi.connect({ username, password, mode: 'live' });
      setStatusData(response.data?.data || { state: 'connected' });
      toast.success('GİB bağlantısı kuruldu');
      setPassword('');
    } catch (error) {
      toast.error(mapErrorMessage(error));
    } finally {
      setLoading((prev) => ({ ...prev, connect: false }));
    }
  };

  const handleImport = async () => {
    if (selectedRange === 'custom' && (!customFrom || !customTo)) {
      toast.error('Özel aralık için başlangıç ve bitiş tarihi girin.');
      return;
    }

    setLoading((prev) => ({ ...prev, import: true }));
    try {
      const response = await gibApi.startImport(activeRange);
      const data = response.data?.data || {};
      setImportSummary({
        imported_invoice_count: data.imported_invoice_count ?? data.invoice_count ?? data.job?.invoice_count ?? 0,
        skipped_count: data.skipped_count ?? data.skipped_missing_identity ?? data.job?.skipped_missing_identity ?? 0,
        parse_error_count: data.parse_error_count ?? data.job?.parse_error_count ?? 0,
        raw_payload_count: data.raw_payload_count ?? data.job?.raw_payload_count ?? 0,
      });
      toast.success('Faturalar çekildi');
      await loadStatus({ silent: true });
    } catch (error) {
      toast.error(mapErrorMessage(error));
    } finally {
      setLoading((prev) => ({ ...prev, import: false }));
    }
  };

  const handleDisconnect = async () => {
    setLoading((prev) => ({ ...prev, disconnect: true }));
    try {
      const response = await gibApi.disconnect();
      setStatusData(response.data?.data || { state: 'not_connected' });
      toast.success('GİB bağlantısı kesildi');
    } catch (error) {
      toast.error(mapErrorMessage(error));
    } finally {
      setLoading((prev) => ({ ...prev, disconnect: false }));
    }
  };

  // --- Outbox Create handlers ---
  const updateOutboxField = (key, value) => setOutboxForm((prev) => ({ ...prev, [key]: value }));

  const updateOutboxLine = (index, key, value) => {
    setOutboxLines((prev) => prev.map((line, idx) => (idx === index ? { ...line, [key]: value } : line)));
  };

  const addOutboxLine = () => {
    setOutboxLines((prev) => [...prev, { name: '', quantity: '1', unit_price: '0.00', vat_rate: '10' }]);
  };

  const removeOutboxLine = (index) => {
    setOutboxLines((prev) => (prev.length <= 1 ? prev : prev.filter((_, idx) => idx !== index)));
  };

  const outboxFormValid = useMemo(() => {
    if (!outboxForm.local_reference_id?.trim()) return false;
    if (!outboxForm.issue_date) return false;
    if (!outboxForm.receiver_vkn?.trim() || !outboxForm.receiver_title?.trim()) return false;
    if (!outboxForm.receiver_city?.trim() || !outboxForm.receiver_district?.trim()) return false;
    if (!outboxLines.length) return false;
    return outboxLines.every((line) =>
      line.name?.trim() &&
      Number(line.quantity) > 0 &&
      Number(line.unit_price) > 0 &&
      Number(line.vat_rate) >= 0
    );
  }, [outboxForm, outboxLines]);

  const handleOutboxCreate = async (event) => {
    event?.preventDefault?.();
    if (!outboxFormValid) {
      toast.error('Zorunlu alanları doldurun.');
      return;
    }
    setOutboxHints([]);
    setLoading((prev) => ({ ...prev, outbox: true }));
    try {
      const payload = {
        local_reference_id: outboxForm.local_reference_id.trim(),
        issue_date: outboxForm.issue_date,
        scenario: 'TEMELFATURA',
        invoice_type_code: 'SATIS',
        document_currency_code: 'TRY',
        receiver: {
          vkn_tckn: outboxForm.receiver_vkn.trim(),
          title: outboxForm.receiver_title.trim(),
          alias: outboxForm.receiver_alias?.trim() || undefined,
          tax_office: outboxForm.receiver_tax_office?.trim() || undefined,
          address: {
            city: outboxForm.receiver_city.trim(),
            district: outboxForm.receiver_district.trim(),
            street: outboxForm.receiver_street?.trim() || undefined,
            postal_code: outboxForm.receiver_postal_code?.trim() || undefined,
            country: 'Türkiye',
          },
        },
        lines: outboxLines.map((line) => ({
          name: line.name.trim(),
          quantity: line.quantity,
          unit_code: 'NIU',
          unit_price: line.unit_price,
          vat_rate: line.vat_rate,
        })),
      };
      const response = await gibApi.createOutboxInvoice(payload);
      const data = response.data?.data || {};
      setOutboxResult({
        id: data.id,
        invoice_number: data.invoice_number,
        provider_status: data.provider_status,
        local_reference_id: data.local_reference_id || payload.local_reference_id,
        http_status: data.http_status,
      });
      toast.success(data.invoice_number ? `Fatura oluşturuldu: ${data.invoice_number}` : 'Fatura gönderildi');
      // Prepare next local_reference_id
      setOutboxForm((prev) => ({ ...prev, local_reference_id: generateLocalRef() }));
    } catch (error) {
      const hints = extractValidationHints(error);
      setOutboxHints(hints);
      toast.error(mapErrorMessage(error));
    } finally {
      setLoading((prev) => ({ ...prev, outbox: false }));
    }
  };

  return (
    <div className="space-y-6" data-testid="gib-connection-page">
      <div className="space-y-2">
        <h1 className="text-4xl font-bold tracking-tight text-slate-900">GİB Bağlantı</h1>
        <p className="text-sm text-slate-500">İnteraktif Vergi Dairesi hesabınızla bağlantı kurun.</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <Card className="rounded-[28px] border-slate-200 shadow-[0_18px_45px_-30px_rgba(15,23,42,0.32)]" data-testid="gib-connection-form-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl"><KeyRound className="h-5 w-5 text-orange-500" /> Bağlantı Bilgileri</CardTitle>
            <CardDescription>Kullanıcı kodunuz ve şifreniz sadece bu sayfanın local state’inde tutulur.</CardDescription>
          </CardHeader>
          <form onSubmit={handleConnect}>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="gib-username">Kullanıcı Kodu</Label>
                <Input id="gib-username" value={username} onChange={(event) => setUsername(event.target.value)} placeholder="İVD kullanıcı kodu" className="h-11 rounded-2xl" data-testid="gib-username-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="gib-password">Şifre</Label>
                <Input id="gib-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Şifreniz" className="h-11 rounded-2xl" data-testid="gib-password-input" />
              </div>
              <Button type="submit" disabled={loading.connect || !username || !password} className="h-11 rounded-2xl bg-orange-500 px-5 text-sm font-semibold hover:bg-orange-600" data-testid="gib-connect-button">
                {loading.connect ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <PlugZap className="mr-2 h-4 w-4" />}Bağlan
              </Button>
            </CardContent>
          </form>
        </Card>

        <Card className="rounded-[28px] border-slate-200 shadow-[0_18px_45px_-30px_rgba(15,23,42,0.32)]" data-testid="gib-status-card">
          <CardHeader>
            <CardTitle className="text-xl">Bağlantı Durumu</CardTitle>
            <CardDescription>Sayfa açıldığında durum otomatik kontrol edilir.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${currentStatus.className}`} data-testid="gib-status-badge">
              {currentStatus.label}
            </div>
            <div className="space-y-2 text-sm text-slate-600">
              <p><span className="font-medium text-slate-900">Son kontrol:</span> {formatDateTime(statusData?.last_verified_at || statusData?.connected_at)}</p>
              <p><span className="font-medium text-slate-900">Kullanıcı:</span> {statusData?.username_masked || '—'}</p>
              <p><span className="font-medium text-slate-900">Durum kodu:</span> {statusData?.last_error || '—'}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="rounded-[28px] border-slate-200 shadow-[0_18px_45px_-30px_rgba(15,23,42,0.32)]" data-testid="gib-import-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl"><CalendarDays className="h-5 w-5 text-orange-500" /> Fatura Çekme</CardTitle>
          <CardDescription>Tarih aralığını seçin ve GİB üzerinden faturaları içe aktarın.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {RANGE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => setSelectedRange(option.value)}
                className={`rounded-2xl border px-4 py-3 text-left text-sm transition-colors ${selectedRange === option.value ? 'border-orange-300 bg-orange-50 text-orange-700' : 'border-slate-200 bg-white text-slate-600'}`}
                data-testid={`gib-range-${option.value}`}
              >
                {option.label}
              </button>
            ))}
          </div>

          {selectedRange === 'custom' && (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="gib-date-from">Başlangıç</Label>
                <Input id="gib-date-from" type="date" value={customFrom} onChange={(event) => setCustomFrom(event.target.value)} className="h-11 rounded-2xl" data-testid="gib-date-from-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="gib-date-to">Bitiş</Label>
                <Input id="gib-date-to" type="date" value={customTo} onChange={(event) => setCustomTo(event.target.value)} className="h-11 rounded-2xl" data-testid="gib-date-to-input" />
              </div>
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <Button type="button" variant="outline" onClick={() => loadStatus()} disabled={loading.status} className="h-11 rounded-2xl" data-testid="gib-status-refresh-button">
              {loading.status ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCcw className="mr-2 h-4 w-4" />}Durumu Kontrol Et
            </Button>
            <Button type="button" onClick={handleImport} disabled={importDisabled} className="h-11 rounded-2xl bg-orange-500 hover:bg-orange-600" data-testid="gib-import-button">
              {loading.import ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle2 className="mr-2 h-4 w-4" />}Faturaları Çek
            </Button>
            <Button type="button" variant="outline" onClick={handleDisconnect} disabled={loading.disconnect} className="h-11 rounded-2xl" data-testid="gib-disconnect-button">
              {loading.disconnect ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Unplug className="mr-2 h-4 w-4" />}Bağlantıyı Kes
            </Button>
          </div>

          {importSummary && (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4" data-testid="gib-import-summary-card">
              <p className="text-sm font-semibold text-slate-900">Son İçe Aktarım Özeti</p>
              <div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-4 text-sm">
                <div><span className="text-slate-500">İşlenen:</span> <span className="font-semibold text-slate-900">{importSummary.imported_invoice_count ?? 0}</span></div>
                <div><span className="text-slate-500">Atlanan:</span> <span className="font-semibold text-slate-900">{importSummary.skipped_count ?? 0}</span></div>
                <div><span className="text-slate-500">Parse Hatası:</span> <span className="font-semibold text-slate-900">{importSummary.parse_error_count ?? 0}</span></div>
                <div><span className="text-slate-500">Ham Kayıt:</span> <span className="font-semibold text-slate-900">{importSummary.raw_payload_count ?? 0}</span></div>
              </div>
            </div>
          )}

          {loading.initial && (
            <div className="rounded-2xl border border-slate-200 bg-white p-4 text-sm text-slate-500" data-testid="gib-initial-loading-state">
              <Loader2 className="mr-2 inline h-4 w-4 animate-spin" /> Durum bilgisi yükleniyor...
            </div>
          )}

          {statusData?.state === 'expired' && (
            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700" data-testid="gib-expired-warning">
              <ShieldAlert className="mr-2 inline h-4 w-4" /> Oturum süresi dolmuş görünüyor. Yeniden bağlanmanız gerekebilir.
            </div>
          )}

          {statusData?.state === 'not_connected' && !loading.initial && (
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600" data-testid="gib-not-connected-hint">
              <CloudOff className="mr-2 inline h-4 w-4" /> Şu an aktif GİB bağlantısı bulunmuyor.
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="rounded-[28px] border-slate-200 shadow-[0_18px_45px_-30px_rgba(15,23,42,0.32)]" data-testid="gib-outbox-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-xl">
            <FileText className="h-5 w-5 text-orange-500" /> Outbox Fatura Oluştur (Turkcell v1)
          </CardTitle>
          <CardDescription>
            Minimal JSON payload ile Turkcell <code className="rounded bg-slate-100 px-1 py-0.5 text-xs">/v1/outboxinvoice/create</code> endpoint'ine fatura gönderir.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleOutboxCreate}>
          <CardContent className="space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="outbox-local-ref">Yerel Referans ID *</Label>
                <Input
                  id="outbox-local-ref"
                  value={outboxForm.local_reference_id}
                  onChange={(event) => updateOutboxField('local_reference_id', event.target.value)}
                  className="h-11 rounded-2xl font-mono text-xs"
                  data-testid="outbox-local-ref-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="outbox-issue-date">Fatura Tarihi *</Label>
                <Input
                  id="outbox-issue-date"
                  type="date"
                  value={outboxForm.issue_date}
                  onChange={(event) => updateOutboxField('issue_date', event.target.value)}
                  className="h-11 rounded-2xl"
                  data-testid="outbox-issue-date-input"
                />
              </div>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 space-y-3">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Alıcı Bilgileri</p>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="outbox-receiver-vkn">VKN / TCKN *</Label>
                  <Input
                    id="outbox-receiver-vkn"
                    value={outboxForm.receiver_vkn}
                    onChange={(event) => updateOutboxField('receiver_vkn', event.target.value)}
                    placeholder="10 veya 11 haneli"
                    className="h-11 rounded-2xl"
                    data-testid="outbox-receiver-vkn-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="outbox-receiver-title">Ünvan / Ad Soyad *</Label>
                  <Input
                    id="outbox-receiver-title"
                    value={outboxForm.receiver_title}
                    onChange={(event) => updateOutboxField('receiver_title', event.target.value)}
                    className="h-11 rounded-2xl"
                    data-testid="outbox-receiver-title-input"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="outbox-receiver-alias">Alıcı Etiketi (opsiyonel)</Label>
                <Input
                  id="outbox-receiver-alias"
                  value={outboxForm.receiver_alias}
                  onChange={(event) => updateOutboxField('receiver_alias', event.target.value)}
                  placeholder="urn:mail:..."
                  className="h-11 rounded-2xl"
                  data-testid="outbox-receiver-alias-input"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="outbox-receiver-tax-office">Vergi Dairesi (opsiyonel)</Label>
                <Input
                  id="outbox-receiver-tax-office"
                  value={outboxForm.receiver_tax_office}
                  onChange={(event) => updateOutboxField('receiver_tax_office', event.target.value)}
                  placeholder="Örn: Marmara Kurumlar"
                  className="h-11 rounded-2xl"
                  data-testid="outbox-receiver-tax-office-input"
                />
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="outbox-receiver-city">Şehir *</Label>
                  <Input
                    id="outbox-receiver-city"
                    value={outboxForm.receiver_city}
                    onChange={(event) => updateOutboxField('receiver_city', event.target.value)}
                    placeholder="İstanbul"
                    className="h-11 rounded-2xl"
                    data-testid="outbox-receiver-city-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="outbox-receiver-district">İlçe *</Label>
                  <Input
                    id="outbox-receiver-district"
                    value={outboxForm.receiver_district}
                    onChange={(event) => updateOutboxField('receiver_district', event.target.value)}
                    placeholder="Kadıköy"
                    className="h-11 rounded-2xl"
                    data-testid="outbox-receiver-district-input"
                  />
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-[minmax(0,2fr)_140px]">
                <div className="space-y-2">
                  <Label htmlFor="outbox-receiver-street">Adres (opsiyonel)</Label>
                  <Input
                    id="outbox-receiver-street"
                    value={outboxForm.receiver_street}
                    onChange={(event) => updateOutboxField('receiver_street', event.target.value)}
                    placeholder="Cadde / Sokak / No"
                    className="h-11 rounded-2xl"
                    data-testid="outbox-receiver-street-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="outbox-receiver-postal-code">Posta Kodu</Label>
                  <Input
                    id="outbox-receiver-postal-code"
                    value={outboxForm.receiver_postal_code}
                    onChange={(event) => updateOutboxField('receiver_postal_code', event.target.value)}
                    placeholder="34000"
                    className="h-11 rounded-2xl"
                    data-testid="outbox-receiver-postal-code-input"
                  />
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Fatura Kalemleri</p>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={addOutboxLine}
                  className="h-9 rounded-xl"
                  data-testid="outbox-add-line-button"
                >
                  <Plus className="mr-1 h-4 w-4" /> Satır Ekle
                </Button>
              </div>
              {outboxLines.map((line, index) => (
                <div key={index} className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-3 sm:grid-cols-[minmax(0,2fr)_100px_140px_100px_40px] sm:items-end" data-testid={`outbox-line-${index}`}>
                  <div className="space-y-1">
                    <Label className="text-xs">Ürün / Hizmet</Label>
                    <Input
                      value={line.name}
                      onChange={(event) => updateOutboxLine(index, 'name', event.target.value)}
                      className="h-10 rounded-xl"
                      data-testid={`outbox-line-${index}-name-input`}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Miktar</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={line.quantity}
                      onChange={(event) => updateOutboxLine(index, 'quantity', event.target.value)}
                      className="h-10 rounded-xl"
                      data-testid={`outbox-line-${index}-quantity-input`}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Birim Fiyat (TL)</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={line.unit_price}
                      onChange={(event) => updateOutboxLine(index, 'unit_price', event.target.value)}
                      className="h-10 rounded-xl"
                      data-testid={`outbox-line-${index}-price-input`}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">KDV %</Label>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      value={line.vat_rate}
                      onChange={(event) => updateOutboxLine(index, 'vat_rate', event.target.value)}
                      className="h-10 rounded-xl"
                      data-testid={`outbox-line-${index}-vat-input`}
                    />
                  </div>
                  <button
                    type="button"
                    onClick={() => removeOutboxLine(index)}
                    disabled={outboxLines.length <= 1}
                    className="flex h-10 items-center justify-center rounded-xl border border-slate-200 text-slate-400 transition hover:border-red-200 hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-40"
                    aria-label="Satırı sil"
                    data-testid={`outbox-line-${index}-remove-button`}
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>

            <Button
              type="submit"
              disabled={!outboxFormValid || loading.outbox}
              className="h-11 w-full rounded-2xl bg-orange-500 hover:bg-orange-600 sm:w-auto"
              data-testid="outbox-submit-button"
            >
              {loading.outbox ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <FileText className="mr-2 h-4 w-4" />}
              Fatura Oluştur
            </Button>

            {outboxResult && (
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800" data-testid="outbox-result-card">
                <p className="text-sm font-semibold text-emerald-900">✅ Başarılı</p>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  <div>
                    <span className="text-emerald-700">Provider ID:</span>{' '}
                    <span className="font-mono text-xs font-semibold" data-testid="outbox-result-id">{outboxResult.id || '—'}</span>
                  </div>
                  <div>
                    <span className="text-emerald-700">Fatura No:</span>{' '}
                    <span className="font-mono text-xs font-semibold" data-testid="outbox-result-invoice-number">{outboxResult.invoice_number || '—'}</span>
                  </div>
                  <div>
                    <span className="text-emerald-700">Durum:</span>{' '}
                    <span className="font-semibold">{outboxResult.provider_status || '—'}</span>
                  </div>
                  <div>
                    <span className="text-emerald-700">Yerel Ref:</span>{' '}
                    <span className="font-mono text-xs">{outboxResult.local_reference_id || '—'}</span>
                  </div>
                </div>
              </div>
            )}

            {outboxHints.length > 0 && (
              <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-800" data-testid="outbox-hints-card">
                <p className="font-semibold text-red-900">Doğrulama Hataları:</p>
                <ul className="mt-2 list-inside list-disc space-y-1">
                  {outboxHints.map((hint, idx) => (
                    <li key={idx} data-testid={`outbox-hint-${idx}`}>{hint}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </form>
      </Card>
    </div>
  );
}
