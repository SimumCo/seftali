# e-Belge Entegrasyonu (Turkcell e-Şirket)

Bu doküman mevcut `services/efatura/*` (UBL v2 upload) katmanına dokunmadan
**additive** olarak eklenen e-Fatura ve e-İrsaliye JSON-create entegrasyonunu anlatır.

> ⚠️ e-Arşiv bu fazda dahil **değildir** (kullanıcı onayı ile ertelendi). Eklenmek
> istendiğinde `services/ebelge/` altına aynı deseni takip eden yeni bir servis modülü
> ve `/api/ebelge/earsiv/*` route'ları konulması yeterlidir.

---

## 1. Environment Değişkenleri

`backend/.env` dosyasına aşağıdaki değişkenler eklendi:

```env
# Ortak API key (zorunlu) — test veya prod ortam key'i
TURKCELL_EBELGE_API_KEY="..."
TURKCELL_EBELGE_ENV="test"        # "test" veya "prod"

# e-Fatura base URL'leri
TURKCELL_EINVOICE_TEST_BASE_URL="https://efaturaservicetest.isim360.com"
TURKCELL_EINVOICE_PROD_BASE_URL="https://efaturaservice.turkcellesirket.com"

# e-İrsaliye base URL'leri
TURKCELL_EIRSLIYE_TEST_BASE_URL="https://eirsaliyeservicetest.isim360.com"
TURKCELL_EIRSLIYE_PROD_BASE_URL="https://eirsaliyeservice.turkcellesirket.com"

# Opsiyonel
TURKCELL_EBELGE_TIMEOUT_SECONDS="20"
TURKCELL_EBELGE_RETRY_ATTEMPTS="3"
```

**Backward compatibility**: Eğer `TURKCELL_EBELGE_API_KEY` boşsa client otomatik olarak
`TURKCELL_X_API_KEY` veya en son `TURKCELL_EINVOICE_API_KEY` değerine düşer (mevcut kurulum bozulmaz).

### Güvenlik
- API key **hiçbir log satırında** yer almaz. `redact_headers` helper'ı tüm istek/yanıt loglarında `x-api-key` ve `Authorization` header'larını `***REDACTED***` yapar.
- Request snapshot'ları `ebelge_documents` collection'a yazılırken `apikey`/`api_key`/`token`/`authorization` içeren anahtarlar redaction'dan geçirilir.
- API key eksikse provider çağrısı **yapılmaz**; 500 + net hata mesajı döner.

---

## 2. Dosya Yapısı

```text
backend/
├── services/ebelge/
│   ├── __init__.py
│   ├── turkcell_client.py       # Ortak HTTP client (x-api-key, retry, redaction)
│   ├── payload_mappers.py       # Frontend sade payload → provider JSON
│   ├── efatura_service.py       # /v1/outboxinvoice/create + /v2/...
│   └── eirsaliye_service.py     # /v1/outboxdespatch/create + /v2/...
├── schemas/ebelge_schemas.py    # Pydantic request/response
├── models/ebelge_document.py    # MongoDB ebelge_documents modeli
├── routes/ebelge_routes.py      # /api/ebelge/* endpoint'leri
└── tests/test_ebelge_integration.py   # Mock-only testler
```

> Mevcut `services/efatura/*` (UBL builder + v2 upload) katmanına **dokunulmadı**.

---

## 3. Endpoint Listesi

Tüm endpoint'ler `/api/ebelge/*` altında. **Yetki: `admin` veya `accounting` rolleri.**

### Sistem
| Method | Path | Açıklama |
|--------|------|----------|
| GET | `/api/ebelge/config/status` | API key var mı, aktif ortam, base URL'ler |
| GET | `/api/ebelge/documents` | Lokal `ebelge_documents` listesi (`document_type=efatura\|eirsaliye`) |

### e-Fatura
| Method | Path | Provider Eşleniği |
|--------|------|--------------------|
| POST | `/api/ebelge/efatura/create` | `POST /v1/outboxinvoice/create` |
| GET | `/api/ebelge/efatura/{id}/status` | `GET /v2/outboxinvoice/{id}/status` |
| GET | `/api/ebelge/efatura/{id}/html?isStandartXslt=true` | `GET /v2/outboxinvoice/{id}/html/{true}` |
| GET | `/api/ebelge/efatura/{id}/pdf?isStandartXslt=true` | `GET /v2/outboxinvoice/{id}/pdf/{true}` (attachment) |
| GET | `/api/ebelge/efatura/{id}/ubl` | `GET /v2/outboxinvoice/{id}/ubl` (attachment) |

### e-İrsaliye
| Method | Path | Provider Eşleniği |
|--------|------|--------------------|
| POST | `/api/ebelge/eirsaliye/create` | `POST /v1/outboxdespatch/create` |
| GET | `/api/ebelge/eirsaliye/{id}/status` | `GET /v2/outboxdespatch/{id}/status` |
| GET | `/api/ebelge/eirsaliye/{id}/html?isStandartXslt=true` | `GET /v2/outboxdespatch/{id}/html/{true}` |
| GET | `/api/ebelge/eirsaliye/{id}/pdf?isStandartXslt=true` | `GET /v2/outboxdespatch/{id}/pdf/{true}` (attachment) |
| GET | `/api/ebelge/eirsaliye/{id}/ubl` | `GET /v2/outboxdespatch/{id}/ubl` (attachment) |
| GET | `/api/ebelge/eirsaliye/{id}/zip` | `GET /v2/outboxdespatch/{id}/zip` (attachment) |

---

## 4. Request / Response Örnekleri

### e-Fatura oluşturma

**Request:**
```http
POST /api/ebelge/efatura/create
Authorization: Bearer <JWT>
Content-Type: application/json

{
  "receiver": {
    "name": "Acme Gıda AŞ",
    "vkn": "1234567890",
    "alias": "urn:mail:defaultpk@acme.com",
    "district": "Kadıköy",
    "city": "İstanbul",
    "country": "Türkiye",
    "street": "Test Cad. No:5",
    "zip_code": "34000",
    "tax_office": "Kadıköy"
  },
  "invoice": {
    "status": 0,
    "local_reference_id": "LOCAL-1",
    "note": "Temmuz teslimatı",
    "profile_type": 0,
    "type": 1,
    "issue_date": "2025-07-15",
    "prefix": "EPA",
    "currency": "TRY"
  },
  "lines": [
    { "name": "Süt Kutusu 1L", "quantity": 10, "unit_code": "NIU", "unit_price": 100, "vat_rate": 20 }
  ]
}
```

**Başarılı response (200):**
```json
{
  "id": "3f6a8a4e-...",             
  "document_type": "efatura",
  "provider_id": "prov-abc",
  "document_number": "EPA2025000001",
  "provider_status": "ok",
  "provider_message": null,
  "local_reference_id": "LOCAL-1",
  "status_internal": "sent",
  "trace_id": null,
  "raw_provider_body": { "Id": "prov-abc", "InvoiceNumber": "EPA2025000001" }
}
```

**Validation hatası (422):**
```json
{
  "detail": {
    "message": "Validation failed",
    "errors": ["receiver.vkn (veya tckn) zorunlu", "lines boş olamaz (en az 1 satır)"]
  }
}
```

**Provider business hatası (400):**
```json
{
  "detail": {
    "message": "VKN hatalı",
    "provider_status": "BusinessException",
    "trace_id": "tr-999",
    "provider_body": { "Error": { "title": "BusinessException", "detail": "VKN hatalı" } }
  }
}
```

### e-İrsaliye oluşturma

```http
POST /api/ebelge/eirsaliye/create
Content-Type: application/json
Authorization: Bearer <JWT>

{
  "receiver": { "name": "Acme", "vkn": "1234567890", "city": "İstanbul" },
  "despatch": { "issue_date": "2025-07-15", "prefix": "EIR" },
  "delivery": { "street": "Teslimat Cad.", "city": "Ankara", "country": "Türkiye" },
  "shipment": {
    "plate_number": "34ABC123",
    "driver_name": "Ali",
    "driver_surname": "Veli",
    "driver_tckn": "12345678901"
  },
  "lines": [
    { "product_name": "Süt Kutusu", "quantity": 5, "unit_code": "C62", "unit_price": 50 }
  ]
}
```

---

## 5. Neden UBL ve JSON-Create Ayrı Tutuluyor?

- Mevcut `services/efatura/` katmanı **UBL XML** üretip `/v2/outboxinvoice` endpoint'ine yüklüyor (gelişmiş senaryolar için).
- Yeni katman ise **sade JSON** kabul edip `/v1/outboxinvoice/create` ve `/v1/outboxdespatch/create` endpoint'lerine basit create çağrısı yapıyor.
- İki akış paralel yaşayabilir, birbirini bozmaz. Frontend istediği akışı seçebilir.
- JSON-create akışı production-ready hale getirildiği için **düşük hacimli, hızlı** oluşturma senaryosunda tercih edilir (formdan direkt belge oluştur).

---

## 6. Internal DB: `ebelge_documents` Collection

Her create denemesi (başarılı/başarısız) yerelde iz bırakır:

```json
{
  "id": "<uuid>",
  "document_type": "efatura | eirsaliye",
  "provider": "turkcell",
  "provider_id": "prov-abc",
  "document_number": "EPA2025000001",
  "local_reference_id": "LOCAL-1",
  "receiver_vkn": "1234567890",
  "receiver_name": "Acme Gıda AŞ",
  "receiver_alias": "urn:mail:...",
  "status_internal": "sent | failed",
  "provider_status": "ok | BusinessException | ...",
  "provider_message": "...",
  "trace_id": "tr-999",
  "request_payload_snapshot": { ... },   // redacted
  "response_payload_snapshot": { ... },  // redacted
  "created_by": "<user.id>",
  "created_by_username": "admin",
  "created_at": "2025-07-15T10:20:30+00:00",
  "updated_at": "..."
}
```

> API key değeri bu koleksiyonda **asla** saklanmaz.

---

## 7. Manual Smoke Test

> ⚠️ Bu adımlar gerçek Turkcell test ortamına istek atar. Production key ile çalıştırmayın.

1. Backend + MongoDB çalışıyor olsun: `sudo supervisorctl status`
2. Admin girişi:
   ```bash
   TOKEN=$(curl -s -X POST http://localhost:8001/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)
   ```
3. Config check:
   ```bash
   curl -s http://localhost:8001/api/ebelge/config/status -H "Authorization: Bearer $TOKEN" | jq
   ```
   Beklenen: `api_key_configured: true`, `environment: "test"`.
4. e-Fatura create (test):
   ```bash
   curl -s -X POST http://localhost:8001/api/ebelge/efatura/create \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d @- <<'JSON'
   {
     "receiver": {"name":"Test","vkn":"1234567890","city":"İstanbul"},
     "invoice": {"issue_date":"2025-07-15","prefix":"EPA","currency":"TRY"},
     "lines": [{"name":"Test","quantity":1,"unit_code":"NIU","unit_price":100,"vat_rate":20}]
   }
   JSON
   ```
5. Status sorgusu:
   ```bash
   curl -s http://localhost:8001/api/ebelge/efatura/<provider_id>/status -H "Authorization: Bearer $TOKEN" | jq
   ```
6. PDF indirme:
   ```bash
   curl -s -o invoice.pdf \
     http://localhost:8001/api/ebelge/efatura/<provider_id>/pdf \
     -H "Authorization: Bearer $TOKEN"
   ```

---

## 8. Otomatik Testler (Mock-Only)

```bash
cd backend
pytest tests/test_ebelge_integration.py -v
```

Testler:
- Payload mapper KDV hesaplamasını doğrular
- Validation hataları (eksik alan) tespit edilir
- Provider 200/400/network hatası senaryoları mock'lanır
- `x-api-key` header'ın doğru eklendiğini doğrular
- Header redaction'ı doğrular
- Base URL seçimi (test ↔ prod) doğrulanır
- Legacy fallback key (TURKCELL_EINVOICE_API_KEY) çalışır
- HTTP 200 + Error body → failure olarak normalize edilir

**Bu testler gerçek provider'a istek atmaz.** Gerçek entegrasyon testleri manuel yapılmalıdır.

---

## 9. Hata Kodları

| HTTP | Anlam |
|------|-------|
| 200 | Başarılı provider response |
| 400 | Provider iş kuralı hatası (message + provider_status + trace_id döner) |
| 401 | JWT eksik / geçersiz |
| 403 | Rol yetkisiz (admin/accounting dışı) |
| 422 | Local validation hatası (eksik/yanlış alan) |
| 500 | API key config eksik |
| 502 | Provider ulaşılamadı (network/timeout) |

---

## 10. Kritik Kurallar

1. ✅ Mevcut `services/efatura/*` **hiç değiştirilmedi**.
2. ✅ Yeni kod eklendi, mevcut endpoint'ler çalışmaya devam ediyor.
3. ✅ Secret redaction uygulandı (log + DB snapshot).
4. ✅ Gerçek provider'a otomatik test yok.
5. ✅ API key yoksa net hata dönüyor, sessiz kalmıyor.
6. ✅ Rol guard: sadece admin + accounting.
