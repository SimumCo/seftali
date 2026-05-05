# e-Fatura Manual Smoke Test

## Gerekli env değişkenleri

`backend/.env` içine:

```env
TURKCELL_EINVOICE_BASE_URL=https://<provider-base-url>
TURKCELL_EINVOICE_CREATE_PATH=/path/to/create
TURKCELL_EINVOICE_STATUS_PATH=/path/to/status
TURKCELL_EINVOICE_STATUS_ID_PARAM=providerInvoiceId
TURKCELL_EINVOICE_API_KEY=your-api-key
TURKCELL_EINVOICE_TIMEOUT_SECONDS=20
TURKCELL_EINVOICE_RETRY_ATTEMPTS=3
```

## Uygulama

Backend çalıştır:

```bash
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

## Test kullanıcı

Yetkili bir kullanıcı ile login olun (`admin`, `accounting`, `sales_agent`, `sales_rep`).

## 1) Test smoke invoice oluştur

```bash
curl -X POST http://localhost:8001/api/invoices/test-smoke \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json"
```

Beklenen:
- local invoice kaydı oluşur
- status `queued` veya `processing` olur
- provider create response kaydedilir

## 2) Invoice durumunu oku

```bash
curl http://localhost:8001/api/invoices/<INVOICE_ID>/status \
  -H "Authorization: Bearer <TOKEN>"
```

## 3) Provider’dan fresh status çek

```bash
curl -X POST http://localhost:8001/api/invoices/<INVOICE_ID>/refresh-status \
  -H "Authorization: Bearer <TOKEN>"
```

Beklenen lifecycle:
- create sonrası: `queued` veya `processing`
- refresh sonrası provider cevabına göre: `sent` veya `failed`

## 4) Batch polling helper

```bash
cd backend
python scripts/dev/poll_einvoice_statuses.py
```

## Bilinen limitler

- provider path’leri env ile verilmeden gerçek create/status çağrısı yapılamaz
- gerçek success-case provider access bilgisi olmadan doğrulanmaz
- UBL XML minimum çalışan yapıda üretildi; provider özel zorunlu ek alanlar varsa env/path kadar mapping de ayrıca sertleştirilmelidir
