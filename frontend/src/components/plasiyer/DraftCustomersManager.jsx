import React, { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Building2, CheckCircle2, FileText, Loader2, Phone, Wallet, X } from 'lucide-react';

import { customerOnboardingAPI } from '../../services/api';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';

const initialForm = {
  customer_type: 'retail',
  risk_limit: 10000,
  balance: 0,
  phone: '',
  address: '',
};

const formatAmount = (value) => Number(value || 0).toLocaleString('tr-TR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const formatDate = (value) => {
  if (!value) return '-';
  try {
    return new Date(value).toLocaleDateString('tr-TR');
  } catch {
    return value;
  }
};

const DraftCustomerApproveModal = ({ item, open, submitting, form, onChange, onClose, onSubmit }) => {
  if (!open || !item) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4" data-testid="draft-customer-approve-modal-overlay">
      <div className="w-full max-w-lg rounded-t-3xl bg-white p-5 shadow-2xl sm:rounded-3xl" data-testid="draft-customer-approve-modal">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">Draft Customer Onayı</p>
            <h3 className="mt-2 text-2xl font-bold text-slate-900">{item.business_name}</h3>
          </div>
          <button type="button" onClick={onClose} className="rounded-2xl border border-slate-200 p-2 text-slate-500" data-testid="draft-customer-approve-close-button">
            <X className="h-5 w-5" />
          </button>
        </div>

        <form className="space-y-4" onSubmit={onSubmit}>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="customer_type">Müşteri Tipi</Label>
              <select
                id="customer_type"
                value={form.customer_type}
                onChange={(event) => onChange('customer_type', event.target.value)}
                className="h-11 w-full rounded-2xl border border-slate-200 bg-white px-3 text-sm"
                data-testid="draft-customer-approve-customer-type"
              >
                <option value="retail">Perakende</option>
                <option value="wholesale">Toptan</option>
                <option value="horeca">HoReCa</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="risk_limit">Risk Limit</Label>
              <Input id="risk_limit" type="number" value={form.risk_limit} onChange={(event) => onChange('risk_limit', event.target.value)} data-testid="draft-customer-approve-risk-limit" className="h-11 rounded-2xl" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="balance">Bakiye</Label>
              <Input id="balance" type="number" value={form.balance} onChange={(event) => onChange('balance', event.target.value)} data-testid="draft-customer-approve-balance" className="h-11 rounded-2xl" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">Telefon</Label>
              <Input id="phone" value={form.phone} onChange={(event) => onChange('phone', event.target.value)} data-testid="draft-customer-approve-phone" className="h-11 rounded-2xl" />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="address">Adres</Label>
            <textarea
              id="address"
              rows={3}
              value={form.address}
              onChange={(event) => onChange('address', event.target.value)}
              className="w-full rounded-2xl border border-slate-200 px-3 py-3 text-sm outline-none focus:border-orange-300"
              data-testid="draft-customer-approve-address"
            />
          </div>

          <Button type="submit" disabled={submitting} className="h-12 w-full rounded-2xl bg-orange-500 text-base font-semibold hover:bg-orange-600" data-testid="draft-customer-approve-submit-button">
            {submitting ? 'Onaylanıyor...' : 'Onayla ve Oluştur'}
          </Button>
        </form>
      </div>
    </div>
  );
};

export const DraftCustomersManager = ({ salespersonId }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedItem, setSelectedItem] = useState(null);
  const [form, setForm] = useState(initialForm);
  const [submitting, setSubmitting] = useState(false);

  const fetchDraftCustomers = async () => {
    if (!salespersonId) {
      setLoading(false);
      setItems([]);
      return;
    }

    try {
      setLoading(true);
      setError('');
      const response = await customerOnboardingAPI.getDraftCustomers(salespersonId);
      setItems(response.data?.data || []);
    } catch (apiError) {
      setError(apiError.response?.data?.detail || 'Draft müşteri listesi yüklenemedi');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDraftCustomers();
  }, [salespersonId]);

  const pendingItems = useMemo(() => items.filter((item) => item.status !== 'approved'), [items]);

  const openApproveModal = (item) => {
    setSelectedItem(item);
    setForm(initialForm);
  };

  const closeApproveModal = () => {
    setSelectedItem(null);
    setSubmitting(false);
  };

  const handleFormChange = (field, value) => {
    setForm((current) => ({ ...current, [field]: value }));
  };

  const handleApprove = async (event) => {
    event.preventDefault();
    if (!selectedItem) return;

    try {
      setSubmitting(true);
      await customerOnboardingAPI.approveDraftCustomer(selectedItem.id, {
        customer_type: form.customer_type,
        risk_limit: Number(form.risk_limit || 0),
        balance: Number(form.balance || 0),
        phone: form.phone,
        address: form.address,
      });
      toast.success('Draft müşteri onaylandı');
      setItems((current) => current.filter((item) => item.id !== selectedItem.id));
      closeApproveModal();
    } catch (apiError) {
      toast.error(apiError.response?.data?.detail || 'Onay işlemi başarısız');
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="rounded-[24px] border border-slate-200 bg-white px-5 py-10 text-center" data-testid="draft-customers-loading-state">
        <Loader2 className="mx-auto h-8 w-8 animate-spin text-orange-500" />
        <p className="mt-3 text-sm text-slate-500">Draft müşteriler yükleniyor...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-[24px] border border-red-200 bg-red-50 px-5 py-6 text-sm text-red-700" data-testid="draft-customers-error-state">
        {error}
      </div>
    );
  }

  if (pendingItems.length === 0) {
    return (
      <div className="rounded-[24px] border border-slate-200 bg-white px-5 py-10 text-center text-slate-500" data-testid="draft-customers-empty-state">
        <CheckCircle2 className="mx-auto h-10 w-10 text-emerald-500" />
        <p className="mt-3 text-base font-medium text-slate-700">Onay bekleyen draft müşteri yok</p>
        <p className="mt-1 text-sm text-slate-400">Yeni import sonrası draft müşteriler burada listelenir.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="draft-customers-manager">
      {pendingItems.map((item) => (
        <div key={item.id} className="rounded-[24px] border border-slate-200 bg-white p-4 shadow-sm" data-testid={`draft-customer-card-${item.id}`}>
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div className="min-w-0 flex-1 space-y-2">
              <div className="flex items-center gap-2 text-slate-900">
                <Building2 className="h-4 w-4 text-slate-400" />
                <h3 className="truncate text-lg font-bold">{item.business_name}</h3>
              </div>
              <div className="flex flex-wrap gap-2 text-xs text-slate-500">
                <span className="rounded-full bg-slate-100 px-3 py-1" data-testid={`draft-customer-identity-${item.id}`}>
                  {item.tc_no || item.tax_number || '-'}
                </span>
                <span className="rounded-full bg-slate-100 px-3 py-1" data-testid={`draft-customer-status-${item.id}`}>
                  {item.status}
                </span>
              </div>
            </div>
            <Button type="button" onClick={() => openApproveModal(item)} className="h-11 rounded-2xl bg-orange-500 px-4 text-sm font-semibold hover:bg-orange-600" data-testid={`draft-customer-approve-button-${item.id}`}>
              Onayla
            </Button>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
            <div className="rounded-2xl bg-slate-50 px-3 py-3">
              <p className="text-xs text-slate-400">Fatura Sayısı</p>
              <p className="mt-1 font-semibold text-slate-800" data-testid={`draft-customer-invoice-count-${item.id}`}>{item.invoice_count || 0}</p>
            </div>
            <div className="rounded-2xl bg-slate-50 px-3 py-3">
              <p className="text-xs text-slate-400">Son Fatura</p>
              <p className="mt-1 font-semibold text-slate-800" data-testid={`draft-customer-last-invoice-${item.id}`}>{formatDate(item.last_invoice_date)}</p>
            </div>
            <div className="rounded-2xl bg-slate-50 px-3 py-3">
              <p className="text-xs text-slate-400">Toplam Tutar</p>
              <p className="mt-1 font-semibold text-slate-800" data-testid={`draft-customer-total-amount-${item.id}`}>{formatAmount(item.total_amount)} TL</p>
            </div>
            <div className="rounded-2xl bg-slate-50 px-3 py-3">
              <p className="text-xs text-slate-400">İletişim</p>
              <p className="mt-1 font-semibold text-slate-800">
                {item.phone || '-'}
              </p>
            </div>
          </div>
        </div>
      ))}

      <DraftCustomerApproveModal
        item={selectedItem}
        open={Boolean(selectedItem)}
        submitting={submitting}
        form={form}
        onChange={handleFormChange}
        onClose={closeApproveModal}
        onSubmit={handleApprove}
      />
    </div>
  );
};
