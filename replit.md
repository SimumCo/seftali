# ŞEFTALİ — Süt Ürünleri B2B Dağıtım Yönetim Sistemi

Türkçe B2B süt ürünleri dağıtım platformu. Müşteri sipariş, plasiyer rota, depo yönetimi ve fatura takibi.

## Run & Operate

- **Backend** workflow: `bash start_backend.sh` → uvicorn FastAPI port 8000
- **Frontend** workflow: `bash start_frontend.sh` → React (CRA+CRACO) port 5000
- **DB seed**: `cd backend && python seed_seftali_data.py`
- **Required env**: `DATABASE_URL`, `SESSION_SECRET`, `MONGO_URL` (legacy, ignored), `DB_NAME` (legacy, ignored), `SECRET_KEY`

## Stack

- **Backend**: FastAPI (Python 3.11), asyncpg, custom MongoDB-compatible JSONB adapter (`backend/config/pg_mongo_adapter.py`)
- **Frontend**: React 18 + CRACO, Tailwind, shadcn/ui, axios, react-router-dom
- **Database**: PostgreSQL (Replit Neon) — JSONB tabanlı; her koleksiyon `{id TEXT PK, doc JSONB}` şeması

## Where things live

- `backend/config/pg_mongo_adapter.py` — MongoDB API'sini PostgreSQL JSONB üzerine çeviren adaptör (find/insert/update/delete/aggregate, $set/$push/$pull/$inc/$addToSet/$unset, upsert)
- `backend/config/database.py` — `db` proxy nesnesi; `db['users']`, `db['sf_products']` vs.
- `backend/routes/` — API endpoint'leri (`/api/auth`, `/api/seftali/admin`, `/api/seftali/sales`, `/api/seftali/customer`)
- `backend/services/seftali/core.py` — `now_utc`, `to_iso`, `gen_id`, koleksiyon sabitleri (COL_*)
- `backend/seed_seftali_data.py` — Demo veri seed'i
- `frontend/src/services/api.js` — axios instance + tüm API tanımları
- `frontend/src/pages/` — Login, dashboard, müşteri/plasiyer/admin sayfaları

## Architecture decisions

- **MongoDB → PostgreSQL JSONB geçişi**: Tüm motor/pymongo bağımlılıkları kaldırıldı. Adaptör sayesinde repository/service kodu MongoDB API'siyle aynı şekilde çalışmaya devam ediyor.
- **Tablo şeması**: Her koleksiyon `CREATE TABLE <name> (id TEXT PRIMARY KEY, doc JSONB)` — sorgular `doc->>...` ile yapılıyor.
- **`create_index` çağrıları kaldırıldı**: PostgreSQL otomatik indexler ve JSONB GIN index gerektiğinde manuel eklenebilir.
- **bulk_write yerine manuel loop**: Adaptör henüz `UpdateOne` operasyonlarını desteklemiyor; `gib_import_repository.py` manuel upsert yapıyor.

## Product

- **Admin**: Müşteri/ürün/depo/plasiyer/kampanya yönetimi, sistem ayarları, bölge tanımları
- **Plasiyer (sales agent)**: Rota haritası, müşteri ziyaretleri, teslimat oluşturma
- **Müşteri**: Sipariş taslağı, ürün katalog, teslimat geçmişi, varyans bildirimi
- **Muhasebe**: Fatura/e-fatura, GİB import, periyodik tüketim hesabı

## Demo Hesapları

| Rol | Kullanıcı | Şifre |
|-----|-----------|-------|
| Admin | `admin` | `admin123` |
| Muhasebe | `muhasebe` | `muhasebe123` |
| Plasiyer | `plasiyer1` | `plasiyer123` |
| Satıcı | `sf_satici` | `satici123` |
| Müşteri A | `sf_musteri` | `musteri123` |
| Müşteri B | `sf_musteri2` | `musteri123` |

## User preferences

- Türkçe iletişim, basit/günlük dil
- Mongo yerine temiz PostgreSQL geçişi tercih edildi (JSONB tabanlı)

## Gotchas

- `services.seftali.utils` modülü YOKTUR; `services.seftali.core`'dan import et
- `backend/.env` içinde `MONGO_URL`/`DB_NAME` hâlâ duruyor ama adaptör kullanmıyor
- Standalone scriptler (`bulk_calculate_consumption.py`, `create_all_demo_users.py`, vs.) hâlâ motor import edebilir — runtime'da çalıştırılmıyorsa sorun değil
- Frontend `REACT_APP_BACKEND_URL` env ile çalışıyor; ayarlanmazsa axios çağrıları kırılır

## Pointers

- Adaptör detayları: `backend/config/pg_mongo_adapter.py`
- Auth flow: `backend/routes/auth_routes.py`, `backend/utils/auth.py`
- API listesi: `http://localhost:8000/docs` (FastAPI Swagger)
