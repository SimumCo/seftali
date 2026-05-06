import React, { useEffect, useState } from 'react';
import { Check, FileText, MapPin, MessageSquare } from 'lucide-react';

const resultOptions = [
  { value: 'visited', label: 'Ziyaret gerçekleşti' },
  { value: 'visited_without_invoice', label: 'Fatura oluşturulmadı' },
  { value: 'not_visited', label: 'Ziyaret gerçekleşmedi' },
];

const actionButtonClass =
  'flex w-full items-center gap-3 rounded-2xl bg-orange-500 px-4 py-3 text-base font-semibold text-white shadow-sm transition-colors hover:bg-orange-600';

const RouteActionModal = ({
  isOpen,
  item,
  onClose,
  onConfirm,
  onOpenLocation,
  onOpenMessages,
  onOpenInvoice,
}) => {
  const [selectedResult, setSelectedResult] = useState(null);

  useEffect(() => {
    if (isOpen && item) {
      setSelectedResult(item.visit_result || null);
    }
  }, [isOpen, item]);

  useEffect(() => {
    if (!isOpen) {
      return undefined;
    }

    const handleEscape = (event) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen || !item) {
    return null;
  }

  const handleConfirm = () => {
    if (!selectedResult) return;
    const nextState =
      selectedResult === 'not_visited'
        ? { status: 'pending', visit_result: 'not_visited' }
        : selectedResult === 'visited_without_invoice'
          ? { status: 'visited', visit_result: 'visited_without_invoice' }
          : { status: 'visited', visit_result: 'visited' };

    onConfirm(item.id, nextState);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/25 px-4 backdrop-blur-[2px]"
      onClick={(event) => {
        if (event.target === event.currentTarget) {
          onClose();
        }
      }}
      data-testid="route-action-modal-overlay"
    >
      <div
        className="w-[calc(100%-2.5rem)] max-w-[34rem] rounded-[28px] border border-slate-200 bg-white p-6 shadow-[0_25px_80px_-30px_rgba(15,23,42,0.45)]"
        data-testid="route-action-modal"
      >
        <h2 className="text-3xl font-bold tracking-tight text-slate-900" data-testid="route-action-modal-title">
          İşlemi Seç
        </h2>

        <div className="mt-5 space-y-3">
          <button
            type="button"
            onClick={() => onOpenLocation(item.id)}
            className={actionButtonClass}
            data-testid="route-action-location-button"
          >
            <MapPin className="h-5 w-5" />
            <span>Konum</span>
          </button>

          <button
            type="button"
            onClick={() => onOpenMessages(item.id)}
            className={actionButtonClass}
            data-testid="route-action-messages-button"
          >
            <MessageSquare className="h-5 w-5" />
            <span>Mesajlar</span>
          </button>

          <button
            type="button"
            onClick={() => onOpenInvoice(item.id)}
            className={actionButtonClass}
            data-testid="route-action-invoice-button"
          >
            <FileText className="h-5 w-5" />
            <span>Fatura Oluştur</span>
          </button>
        </div>

        <div className="mt-5 border-t border-slate-200 pt-4">
          <p className="text-2xl font-semibold text-slate-800" data-testid="route-action-modal-label">
            Fatura oluşturmadan devam et
          </p>

          <div className="mt-4 space-y-1">
            {resultOptions.map((option) => {
              const isSelected = selectedResult === option.value;

              return (
                <button
                  key={option.value}
                  type="button"
                  onClick={() => setSelectedResult(option.value)}
                  className="flex w-full items-center gap-3 rounded-2xl px-2 py-2 text-left transition-colors hover:bg-slate-50"
                  data-testid={`route-action-option-${option.value}`}
                >
                  <span
                    className={`flex h-7 w-7 items-center justify-center rounded-lg border ${
                      isSelected
                        ? 'border-emerald-500 bg-emerald-500 text-white'
                        : 'border-slate-300 bg-white text-transparent'
                    }`}
                    data-testid={`route-action-option-indicator-${option.value}`}
                  >
                    <Check className="h-4 w-4" />
                  </span>
                  <span className="text-xl text-slate-800">{option.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <button
          type="button"
          onClick={handleConfirm}
          disabled={!selectedResult}
          className="mt-5 w-full rounded-2xl bg-orange-500 px-4 py-3 text-3xl font-semibold text-white shadow-sm transition-colors hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300"
          data-testid="route-action-confirm-button"
        >
          Seç
        </button>
      </div>
    </div>
  );
};

export default RouteActionModal;
