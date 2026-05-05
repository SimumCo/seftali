import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';
import { Navigate } from 'react-router-dom';
import LogoutButton from '../components/ui/LogoutButton';

const API_BASE = `${process.env.REACT_APP_BACKEND_URL}/api`;

const buildAuthHeader = () => {
  const token = localStorage.getItem('token') || localStorage.getItem('customer_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const defaultEFaturaForm = () => ({
  receiver: {
    name: '',
    vkn: '',
    alias: '',
    district: '',
    city: 'İstanbul',
    country: 'Türkiye',
    street: '',
    zip_code: '',
    tax_office: '',
  },
  invoice: {
    issue_date: new Date().toISOString().slice(0, 10),
    prefix: 'EPA',
    currency: 'TRY',
    note: '',
  },
  line: {
    name: '',
    quantity: 1,
    unit_code: 'NIU',
    unit_price: 0,
    vat_rate: 20,
  },
});

const defaultEIrsaliyeForm = () => ({
  receiver: {
    name: '',
    vkn: '',
    alias: '',
    district: '',
    city: 'İstanbul',
    country: 'Türkiye',
    street: '',
    zip_code: '',
    tax_office: '',
  },
  despatch: {
    issue_date: new Date().toISOString().slice(0, 10),
    prefix: 'EIR',
    currency: 'TRY',
    note: '',
  },
  delivery: { street: '', district: '', city: '', country: 'Türkiye', zip_code: '' },
  shipment: { plate_number: '', driver_name: '', driver_surname: '', driver_tckn: '' },
  line: { product_name: '', quantity: 1, unit_code: 'C62', unit_price: 0 },
});

const extractErrorMessage = (error) => {
  const detail = error?.response?.data?.detail;
  if (!detail) return error?.message || 'Bilinmeyen hata';
  if (typeof detail === 'string') return detail;
  if (detail.message) {
    const parts = [detail.message];
    if (detail.provider_status) parts.push(`(${detail.provider_status})`);
    if (Array.isArray(detail.errors) && detail.errors.length) parts.push(`- ${detail.errors.join(', ')}`);
    if (detail.trace_id) parts.push(`traceId: ${detail.trace_id}`);
    return parts.join(' ');
  }
  return JSON.stringify(detail).slice(0, 300);
};

const DocumentResultCard = ({ result, onDownload, kind }) => {
  if (!result) return null;
  const providerId = result.provider_id;
  const basePath = kind === 'efatura' ? 'efatura' : 'eirsaliye';

  return (
    <Alert className="mt-4 border-emerald-200 bg-emerald-50">
      <AlertTitle className="text-emerald-800">✅ Belge oluşturuldu</AlertTitle>
      <AlertDescription className="text-sm space-y-1 text-emerald-900">
        <div><strong>Provider ID:</strong> {providerId || '-'}</div>
        <div><strong>Belge No:</strong> {result.document_number || '-'}</div>
        <div><strong>Durum:</strong> {result.provider_status || result.status_internal}</div>
        {result.local_reference_id && (
          <div><strong>Yerel Ref:</strong> {result.local_reference_id}</div>
        )}
        {providerId && (
          <div className="flex flex-wrap gap-2 pt-2">
            <Button size="sm" variant="outline" onClick={() => onDownload(basePath, providerId, 'html', 'html')}>
              HTML Görüntüle
            </Button>
            <Button size="sm" variant="outline" onClick={() => onDownload(basePath, providerId, 'pdf', 'pdf')}>
              PDF İndir
            </Button>
            <Button size="sm" variant="outline" onClick={() => onDownload(basePath, providerId, 'ubl', 'xml')}>
              UBL (XML) İndir
            </Button>
            {kind === 'eirsaliye' && (
              <Button size="sm" variant="outline" onClick={() => onDownload(basePath, providerId, 'zip', 'zip')}>
                ZIP İndir
              </Button>
            )}
          </div>
        )}
      </AlertDescription>
    </Alert>
  );
};

const ErrorBlock = ({ error }) => {
  if (!error) return null;
  return (
    <Alert className="mt-4 border-red-200 bg-red-50">
      <AlertTitle className="text-red-800">❌ İşlem başarısız</AlertTitle>
      <AlertDescription className="text-sm text-red-900 whitespace-pre-wrap">
        {error}
      </AlertDescription>
    </Alert>
  );
};

const downloadProviderAsset = async (basePath, providerId, assetKind, ext) => {
  try {
    const response = await axios.get(
      `${API_BASE}/ebelge/${basePath}/${providerId}/${assetKind}`,
      {
        headers: buildAuthHeader(),
        responseType: assetKind === 'html' ? 'text' : 'blob',
      },
    );

    if (assetKind === 'html') {
      const win = window.open('', '_blank');
      if (win) {
        win.document.write(response.data);
        win.document.close();
      } else {
        toast.error('Popup engelleyici HTML önizlemesini bloklamış olabilir.');
      }
      return;
    }

    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${basePath}-${providerId}.${ext}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  } catch (err) {
    toast.error(`İndirme hatası: ${extractErrorMessage(err)}`);
  }
};

const EFaturaForm = () => {
  const [form, setForm] = useState(defaultEFaturaForm());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (section, key, value) => {
    setForm((prev) => ({ ...prev, [section]: { ...prev[section], [key]: value } }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    const payload = {
      receiver: form.receiver,
      invoice: form.invoice,
      lines: [
        {
          name: form.line.name,
          quantity: Number(form.line.quantity),
          unit_code: form.line.unit_code,
          unit_price: Number(form.line.unit_price),
          vat_rate: Number(form.line.vat_rate),
        },
      ],
    };

    try {
      const { data } = await axios.post(`${API_BASE}/ebelge/efatura/create`, payload, {
        headers: buildAuthHeader(),
      });
      setResult(data);
      toast.success('e-Fatura oluşturuldu');
    } catch (err) {
      const msg = extractErrorMessage(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <Label>Alıcı Unvan *</Label>
          <Input value={form.receiver.name} onChange={(e) => handleChange('receiver', 'name', e.target.value)} required />
        </div>
        <div>
          <Label>VKN / TCKN *</Label>
          <Input value={form.receiver.vkn} onChange={(e) => handleChange('receiver', 'vkn', e.target.value)} required />
        </div>
        <div>
          <Label>Alias / Email</Label>
          <Input value={form.receiver.alias} onChange={(e) => handleChange('receiver', 'alias', e.target.value)} placeholder="urn:mail:defaultpk@firma.com" />
        </div>
        <div>
          <Label>Vergi Dairesi</Label>
          <Input value={form.receiver.tax_office} onChange={(e) => handleChange('receiver', 'tax_office', e.target.value)} />
        </div>
        <div>
          <Label>İl</Label>
          <Input value={form.receiver.city} onChange={(e) => handleChange('receiver', 'city', e.target.value)} />
        </div>
        <div>
          <Label>İlçe</Label>
          <Input value={form.receiver.district} onChange={(e) => handleChange('receiver', 'district', e.target.value)} />
        </div>
        <div className="md:col-span-2">
          <Label>Adres</Label>
          <Input value={form.receiver.street} onChange={(e) => handleChange('receiver', 'street', e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t">
        <div>
          <Label>Fatura Tarihi *</Label>
          <Input type="date" value={form.invoice.issue_date} onChange={(e) => handleChange('invoice', 'issue_date', e.target.value)} required />
        </div>
        <div>
          <Label>Prefix</Label>
          <Input value={form.invoice.prefix} onChange={(e) => handleChange('invoice', 'prefix', e.target.value)} />
        </div>
        <div>
          <Label>Para Birimi</Label>
          <Input value={form.invoice.currency} onChange={(e) => handleChange('invoice', 'currency', e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-3 pt-2 border-t">
        <div className="md:col-span-2">
          <Label>Ürün Adı *</Label>
          <Input value={form.line.name} onChange={(e) => handleChange('line', 'name', e.target.value)} required />
        </div>
        <div>
          <Label>Miktar *</Label>
          <Input type="number" min="0" step="0.001" value={form.line.quantity} onChange={(e) => handleChange('line', 'quantity', e.target.value)} required />
        </div>
        <div>
          <Label>Birim Fiyat *</Label>
          <Input type="number" min="0" step="0.0001" value={form.line.unit_price} onChange={(e) => handleChange('line', 'unit_price', e.target.value)} required />
        </div>
        <div>
          <Label>KDV %</Label>
          <Input type="number" min="0" step="0.01" value={form.line.vat_rate} onChange={(e) => handleChange('line', 'vat_rate', e.target.value)} />
        </div>
      </div>

      <Button type="submit" disabled={loading} className="w-full md:w-auto">
        {loading ? 'Gönderiliyor...' : 'e-Fatura Oluştur'}
      </Button>

      <DocumentResultCard result={result} onDownload={downloadProviderAsset} kind="efatura" />
      <ErrorBlock error={error} />
    </form>
  );
};

const EIrsaliyeForm = () => {
  const [form, setForm] = useState(defaultEIrsaliyeForm());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleChange = (section, key, value) => {
    setForm((prev) => ({ ...prev, [section]: { ...prev[section], [key]: value } }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setResult(null);
    setLoading(true);

    const payload = {
      receiver: form.receiver,
      despatch: form.despatch,
      delivery: form.delivery,
      shipment: form.shipment,
      lines: [
        {
          product_name: form.line.product_name,
          quantity: Number(form.line.quantity),
          unit_code: form.line.unit_code,
          unit_price: Number(form.line.unit_price),
        },
      ],
    };

    try {
      const { data } = await axios.post(`${API_BASE}/ebelge/eirsaliye/create`, payload, {
        headers: buildAuthHeader(),
      });
      setResult(data);
      toast.success('e-İrsaliye oluşturuldu');
    } catch (err) {
      const msg = extractErrorMessage(err);
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div>
          <Label>Alıcı Unvan *</Label>
          <Input value={form.receiver.name} onChange={(e) => handleChange('receiver', 'name', e.target.value)} required />
        </div>
        <div>
          <Label>VKN / TCKN *</Label>
          <Input value={form.receiver.vkn} onChange={(e) => handleChange('receiver', 'vkn', e.target.value)} required />
        </div>
        <div>
          <Label>Alias</Label>
          <Input value={form.receiver.alias} onChange={(e) => handleChange('receiver', 'alias', e.target.value)} />
        </div>
        <div>
          <Label>Vergi Dairesi</Label>
          <Input value={form.receiver.tax_office} onChange={(e) => handleChange('receiver', 'tax_office', e.target.value)} />
        </div>
        <div>
          <Label>İl</Label>
          <Input value={form.receiver.city} onChange={(e) => handleChange('receiver', 'city', e.target.value)} />
        </div>
        <div>
          <Label>İlçe</Label>
          <Input value={form.receiver.district} onChange={(e) => handleChange('receiver', 'district', e.target.value)} />
        </div>
        <div className="md:col-span-2">
          <Label>Adres</Label>
          <Input value={form.receiver.street} onChange={(e) => handleChange('receiver', 'street', e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t">
        <div>
          <Label>İrsaliye Tarihi *</Label>
          <Input type="date" value={form.despatch.issue_date} onChange={(e) => handleChange('despatch', 'issue_date', e.target.value)} required />
        </div>
        <div>
          <Label>Prefix</Label>
          <Input value={form.despatch.prefix} onChange={(e) => handleChange('despatch', 'prefix', e.target.value)} />
        </div>
        <div>
          <Label>Para Birimi</Label>
          <Input value={form.despatch.currency} onChange={(e) => handleChange('despatch', 'currency', e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-2 border-t">
        <div className="md:col-span-2">
          <Label>Teslimat Adresi</Label>
          <Input value={form.delivery.street} onChange={(e) => handleChange('delivery', 'street', e.target.value)} />
        </div>
        <div>
          <Label>Teslimat İli</Label>
          <Input value={form.delivery.city} onChange={(e) => handleChange('delivery', 'city', e.target.value)} />
        </div>
        <div>
          <Label>Plaka</Label>
          <Input value={form.shipment.plate_number} onChange={(e) => handleChange('shipment', 'plate_number', e.target.value)} placeholder="34ABC123" />
        </div>
        <div>
          <Label>Sürücü Ad</Label>
          <Input value={form.shipment.driver_name} onChange={(e) => handleChange('shipment', 'driver_name', e.target.value)} />
        </div>
        <div>
          <Label>Sürücü Soyad</Label>
          <Input value={form.shipment.driver_surname} onChange={(e) => handleChange('shipment', 'driver_surname', e.target.value)} />
        </div>
        <div>
          <Label>Sürücü TCKN</Label>
          <Input value={form.shipment.driver_tckn} onChange={(e) => handleChange('shipment', 'driver_tckn', e.target.value)} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 pt-2 border-t">
        <div className="md:col-span-2">
          <Label>Ürün Adı *</Label>
          <Input value={form.line.product_name} onChange={(e) => handleChange('line', 'product_name', e.target.value)} required />
        </div>
        <div>
          <Label>Miktar *</Label>
          <Input type="number" min="0" step="0.001" value={form.line.quantity} onChange={(e) => handleChange('line', 'quantity', e.target.value)} required />
        </div>
        <div>
          <Label>Birim Fiyat</Label>
          <Input type="number" min="0" step="0.0001" value={form.line.unit_price} onChange={(e) => handleChange('line', 'unit_price', e.target.value)} />
        </div>
      </div>

      <Button type="submit" disabled={loading} className="w-full md:w-auto">
        {loading ? 'Gönderiliyor...' : 'e-İrsaliye Oluştur'}
      </Button>

      <DocumentResultCard result={result} onDownload={downloadProviderAsset} kind="eirsaliye" />
      <ErrorBlock error={error} />
    </form>
  );
};

const EArsivPlaceholder = () => (
  <Alert className="border-amber-300 bg-amber-50">
    <AlertTitle>e-Arşiv</AlertTitle>
    <AlertDescription>
      e-Arşiv entegrasyonu bu fazda devre dışı bırakıldı. Provider JSON create endpoint'i netleştiğinde
      aynı desen takip edilerek eklenecek. Şimdilik e-Fatura ve e-İrsaliye kullanılabilir.
    </AlertDescription>
  </Alert>
);

const ConfigBanner = () => {
  const [status, setStatus] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios
      .get(`${API_BASE}/ebelge/config/status`, { headers: buildAuthHeader() })
      .then(({ data }) => setStatus(data))
      .catch((err) => setError(extractErrorMessage(err)));
  }, []);

  if (error) {
    return <Alert className="border-red-200 bg-red-50 mb-4"><AlertDescription>{error}</AlertDescription></Alert>;
  }
  if (!status) return null;

  return (
    <Alert className={`mb-4 ${status.api_key_configured ? 'border-emerald-200 bg-emerald-50' : 'border-red-300 bg-red-50'}`}>
      <AlertTitle>Provider durumu</AlertTitle>
      <AlertDescription className="text-sm">
        Ortam: <strong>{status.environment.toUpperCase()}</strong> ·{' '}
        API Key: <strong>{status.api_key_configured ? 'OK' : 'EKSİK'}</strong>
        {status.has_legacy_fallback && !status.api_key_configured
          ? ' (legacy fallback kullanılabilir)'
          : ''}
        <div className="text-xs text-slate-600 mt-1">
          e-Fatura: {status.efatura_base_url} · e-İrsaliye: {status.eirsaliye_base_url}
        </div>
      </AlertDescription>
    </Alert>
  );
};

const EBelgePage = () => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  if (!['admin', 'accounting'].includes(user.role)) return <Navigate to="/" replace />;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="bg-white border-b">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-slate-900">e-Belge (Turkcell)</h1>
            <p className="text-sm text-slate-500">e-Fatura &amp; e-İrsaliye oluşturma · sadece admin/muhasebe</p>
          </div>
          <LogoutButton />
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-4 py-6">
        <ConfigBanner />

        <Tabs defaultValue="efatura" className="w-full">
          <TabsList className="grid grid-cols-3 max-w-md">
            <TabsTrigger value="efatura">e-Fatura</TabsTrigger>
            <TabsTrigger value="eirsaliye">e-İrsaliye</TabsTrigger>
            <TabsTrigger value="earsiv">e-Arşiv</TabsTrigger>
          </TabsList>

          <TabsContent value="efatura" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle>e-Fatura Oluştur</CardTitle>
              </CardHeader>
              <CardContent>
                <EFaturaForm />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="eirsaliye" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle>e-İrsaliye Oluştur</CardTitle>
              </CardHeader>
              <CardContent>
                <EIrsaliyeForm />
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="earsiv" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle>e-Arşiv</CardTitle>
              </CardHeader>
              <CardContent>
                <EArsivPlaceholder />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default EBelgePage;
