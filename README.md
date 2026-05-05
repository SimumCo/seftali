# Dağıtım Yönetim Sistemi

Süt ve süt ürünleri dağıtımı için geliştirilmiş, rol tabanlı (admin, muhasebe, plasiyer, üretim, depo, bakım, müşteri) bir **B2B Dağıtım Yönetim Platformu**.

- **Backend**: FastAPI + MongoDB + JWT
- **Frontend**: React (CRA + CRACO) + TailwindCSS + shadcn/ui
- **Veritabanı**: MongoDB (motor / async)
- **Entegrasyon**: Turkcell e-Fatura (outbox), GİB import, HTML/SED fatura parsing
- **Modül**: ŞEFTALİ (plasiyer saha operasyonu modülü)

> Yol haritası: [ROADMAP.md](./ROADMAP.md) • Özet: [ROADMAP_SUMMARY.md](./ROADMAP_SUMMARY.md)
> DB şeması: [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md) • İlişkiler: [DATABASE_RELATIONSHIPS.md](./DATABASE_RELATIONSHIPS.md)

---

## İçindekiler

- [Özellikler](#özellikler)
- [Mimari](#mimari)
- [Proje Yapısı](#proje-yapısı)
- [Kurulum](#kurulum)
- [Çalıştırma (Supervisor)](#çalıştırma-supervisor)
- [Demo Hesaplar](#demo-hesaplar)
- [Rol Bazlı Paneller](#rol-bazlı-paneller)
- [API Modülleri](#api-modülleri)
- [Seed Scriptleri](#seed-scriptleri)
- [Test](#test)
- [Sorun Giderme](#sorun-giderme)

---

## Özellikler

### 🧠 Akıllı Sipariş (Smart Orders)
- Müşteri tüketim geçmişi + mevcut stok üzerinden öneri üretimi
- Plasiyer için depo sipariş önerisi (warehouse-draft)
- Canonical alias: `/seftali/smart-orders` (legacy `warehouse-draft` yolu da çalışır)

### 📄 Fatura Yönetimi
- **HTML fatura yükleme** (BeautifulSoup parser)
- **SED format** desteği (Türkçe karakter + lineTable + customerIDTable)
- **Manuel fatura girişi** (otomatik müşteri/ürün oluşturma + vergi no lookup)
- **GİB import** (CSV/Excel toplu fatura içe aktarma)
- **Turkcell e-Fatura outbox** entegrasyonu (v1 JSON)

### 📊 Tüketim Analizi
- **Fatura bazlı tüketim hesaplama** – aynı ürünün önceki faturalarda geriye dönük aranması (`product_code` eşleşmesi)
- **Periyodik tüketim**: haftalık & aylık aggregation
- **Yıllık karşılaştırma** (YoY): `percentage_change`, `trend_direction` (growth/decline/stable/no_data)
- **Mevsimsel analiz**: kış/yaz tüketim farkı + `expected_consumption` / `deviation_rate`
- **Top consumers** raporu (ürün bazlı en çok tüketen müşteriler)

### 👥 Kullanıcı Yönetimi
- JWT auth + rol tabanlı yetkilendirme (`admin`, `accounting`, `sales_agent`, `customer`, `production_manager`, `production_operator`, `quality_control`, `warehouse_manager`, `warehouse_staff`, `warehouse_supervisor`, `maintenance_technician`)
- CRUD + şifre değiştirme + aktif/deaktif + kalıcı silme
- Müşteri otomatik oluşturma (vergi no lookup ile)

### 🏭 Üretim Yönetimi
- Üretim hatları, BOM (reçeteler), üretim planları, üretim emirleri
- Operatör ataması + kalite kontrol
- Hammadde analizi + dashboard istatistikleri

### 🏪 Depo & Stok
- Çoklu depo yönetimi (İstanbul, Ankara, İzmir, Bursa, Antalya, Adana vb.)
- Stok bildirimleri, kritik stok uyarıları
- Warehouse Manager / Staff / Supervisor panelleri

### 📢 Kampanya Sistemi
- **Basit İndirim** (% veya TL)
- **X Al Y Kazan** (hediye)
- **Toplu Alım İndirimi** (birim fiyat)
- VIP / sezonluk / yeni müşteri kampanyaları

### 🚚 Plasiyer (Sales Agent) Operasyonu
- Haftalık müşteri rotası (Pazartesi-Cumartesi)
- Depoya kendi stoğu için sipariş (warehouse order)
- Müşteri adına sipariş
- Teslimat takibi
- Kampanya uygulama

### 🛎️ Bildirimler & Geri Bildirim
- Notifications API (unread count, create, list)
- Customer feedback (memnuniyet + şikâyet)
- Maintenance / fault report akışı

---

## Mimari

### Domain-based route yapısı

```
backend/routes/
├── auth_routes.py              # /api/auth/*
├── customer_auth_routes.py     # /api/auth/customer/*
├── users_routes.py             # /api/users/*
├── products.py                 # /api/products/*
├── invoices_routes.py          # /api/invoices/*
├── gib_import_routes.py        # /api/gib/*, /api/draft-customers, /api/customers/*
├── gib_live_routes.py          # /api/gib/live/*
└── seftali/                    # /api/seftali/*
    ├── smart_orders.py         # akıllı sipariş
    ├── stock.py                # plasiyer stok
    ├── customers.py            # plasiyer müşteri
    ├── orders.py               # plasiyer sipariş
    ├── deliveries.py           # plasiyer teslimat
    ├── campaigns.py            # kampanya listeleme
    ├── customer_routes.py      # müşteri-facing endpoint
    ├── admin_routes.py         # admin endpoint
    └── sales_routes.py         # legacy / ambiguous leftover
```

### Katman sorumluları

| Katman | Sorumluluk |
|--------|-----------|
| `routes/` | HTTP katmanı, request/response, auth wiring |
| `services/` | Business logic, domain façade |
| `models/` | Pydantic & Mongo veri modelleri (UUID primary key) |
| `repositories/` | Veri erişim katmanı (kademeli genişletiliyor) |
| `schemas/` | Request/response schema'ları |
| `middleware/` | Auth, CORS, loglama |
| `config/` | Settings & DB bağlantısı |

### Önemli servisler

- `services/invoice_service.py` – HTML/SED/Turkcell parsing
- `services/consumption_calculation_service.py` – fatura bazlı tüketim
- `services/periodic_consumption_service.py` – haftalık/aylık aggregation
- `services/production_service.py` – üretim iş akışı
- `services/campaign_service.py` – kampanya motoru
- `services/notification_service.py` – bildirim orkestrasyonu
- `services/efatura/` – Turkcell outbox adapter
- `services/gib_import/` – GİB CSV/Excel import
- `services/seftali/core/` – plasiyer domain façade

---

## Proje Yapısı

```text
/app
├── backend/
│   ├── config/                 # DB bağlantısı & settings
│   ├── middleware/             # auth & ortak middleware
│   ├── models/                 # Pydantic modelleri (UUID)
│   ├── repositories/           # veri erişim katmanı
│   ├── routes/                 # FastAPI route modülleri
│   │   └── seftali/            # ŞEFTALİ (plasiyer) domain
│   ├── schemas/                # request/response şemaları
│   ├── services/               # business logic
│   │   ├── efatura/            # Turkcell e-fatura
│   │   ├── gib_import/         # GİB import
│   │   └── seftali/core/       # plasiyer core
│   ├── scripts/                # ad-hoc betikler
│   ├── tests/                  # backend pytest testleri
│   ├── seed_*.py               # seed scriptleri
│   ├── reset_demo_accounts.py  # demo hesap resetleme
│   ├── requirements.txt
│   └── server.py               # FastAPI app entry
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/         # ortak + rol bazlı componentler
│   │   │   ├── admin/
│   │   │   ├── customer/
│   │   │   ├── plasiyer/
│   │   │   ├── production/
│   │   │   ├── shared/
│   │   │   └── ui/             # shadcn/ui
│   │   ├── pages/              # rol bazlı dashboardlar
│   │   └── services/           # frontend API katmanı
│   ├── craco.config.js
│   ├── tailwind.config.js
│   └── package.json
│
├── scripts/                    # kök seviye yardımcı betikler
├── tests/                      # kök seviye test yardımcıları
├── memory/                     # PRD + test credentials
├── docs/                       # dokümantasyon
├── DATABASE_SCHEMA.md
├── DATABASE_RELATIONSHIPS.md
├── ROADMAP.md
├── ROADMAP_SUMMARY.md
├── GITHUB_DEPLOYMENT.md
└── README.md                   # bu dosya
```

---

## Kurulum

### Gereksinimler

- Python **3.11+**
- Node.js **16+**
- Yarn (npm kullanmayın)
- MongoDB 6+

### 1) Backend

```bash
cd backend
pip install -r requirements.txt
```

`backend/.env` (kök dizindeki mevcut `.env` örneği):

```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="distribution_management"
SECRET_KEY="change-me"
CORS_ORIGINS="http://localhost:3000"
DEBUG="False"
DEFAULT_CUSTOMER_PASSWORD="123123"

# Turkcell e-Fatura (opsiyonel)
TURKCELL_EINVOICE_BASE_URL="https://efaturaservicetest.isim360.com"
TURKCELL_EINVOICE_API_KEY="..."
TURKCELL_OUTBOX_CREATE_PATH="/v1/outboxinvoice/create"
```

> ⚠️ Production ortamında `MONGO_URL`, `SECRET_KEY` ve Turkcell API key değerlerini kesinlikle değiştirin.

### 2) Frontend

```bash
cd frontend
yarn install
```

`frontend/.env`:

```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

### 3) Veritabanını seed et

```bash
cd backend
python reset_demo_accounts.py           # demo kullanıcılar (admin, plasiyer1…, musteri1…)
python seed_seftali_data.py             # ŞEFTALİ modülü (ürünler, müşteriler, teslimatlar)
python seed_warehouses.py               # depolar
python seed_advanced_campaigns.py       # kampanyalar
python seed_production_data.py          # üretim hatları, BOM, planlar
python seed_maintenance_data.py         # bakım görevleri
```

---

## Çalıştırma (Supervisor)

Platform `supervisor` altında çalışır (container ortamı). Manuel restart:

```bash
sudo supervisorctl status
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
sudo supervisorctl restart all
```

Logları izleme:

```bash
tail -f /var/log/supervisor/backend.err.log
tail -f /var/log/supervisor/backend.out.log
tail -f /var/log/supervisor/frontend.err.log
tail -f /var/log/supervisor/frontend.out.log
```

### Manuel geliştirme (supervisor kullanmadan)

```bash
# Backend
cd backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload

# Frontend
cd frontend
yarn start
```

**Erişim:**
- Frontend: http://localhost:3000
- Backend: http://localhost:8001
- Swagger: http://localhost:8001/docs

---

## Demo Hesaplar

> Seed: `backend/reset_demo_accounts.py`

### 🔧 Yönetim
| Rol | Kullanıcı | Şifre |
|-----|-----------|-------|
| Admin | `admin` | `admin123` |
| Warehouse Manager | `manager` | `manager123` |
| Warehouse Staff | `staff` | `staff123` |

### 👔 Saha
| Rol | Kullanıcı | Şifre |
|-----|-----------|-------|
| Satış Temsilcisi | `satistemsilcisi` | `satis123` |
| Plasiyer 1 | `plasiyer1` | `plasiyer123` |
| Plasiyer 2 | `plasiyer2` | `plasiyer123` |
| Plasiyer 3 | `plasiyer3` | `plasiyer123` |

### 👥 Müşteriler
| Rol | Kullanıcı | Şifre |
|-----|-----------|-------|
| Müşteri 1 | `musteri1` | `musteri123` |
| Müşteri 2 | `musteri2` | `musteri123` |
| Müşteri 3 | `musteri3` | `musteri123` |

### 🍑 ŞEFTALİ Modülü
> Seed: `backend/seed_seftali_data.py`

| Rol | Kullanıcı | Şifre |
|-----|-----------|-------|
| Seftali Plasiyer | `sf_plasiyer` | `plasiyer123` |
| Seftali Müşteri A | `sf_musteri` | `musteri123` |
| Seftali Müşteri B | `sf_musteri2` | `musteri123` |
| Seftali Satıcı | `sf_satici` | `satici123` |

---

## Rol Bazlı Paneller

Her rol için ayrı bir dashboard sayfası bulunur (`frontend/src/pages/`):

| Dashboard | Dosya | Hedef Rol |
|-----------|-------|-----------|
| Admin Dashboard | `AdminDashboard.js` | `admin` |
| Accounting Dashboard | `AccountingDashboard.js` | `accounting` |
| Customer Dashboard | `CustomerDashboard.js` | `customer` |
| Plasiyer Dashboard | `PlasiyerDashboard.js` / `PlasiyerDashboardShell.jsx` | `sales_agent` |
| Sales Agent Dashboard | `SalesAgentDashboard.js` | `sales_agent` |
| Sales Rep Dashboard | `SalesRepDashboard.js` | `sales_rep` |
| Production Manager | `ProductionManagerDashboard.js` | `production_manager` |
| Production Operator | `ProductionOperatorDashboard.js` | `production_operator` |
| Quality Control | `QualityControlDashboard.js` | `quality_control` |
| Warehouse Manager | `WarehouseManagerDashboard.js` | `warehouse_manager` |
| Warehouse Staff | `WarehouseStaffDashboard.js` | `warehouse_staff` |
| Warehouse Supervisor | `WarehouseSupervisorDashboard.js` | `warehouse_supervisor` |
| Maintenance Tech. | `MaintenanceTechnicianDashboard.js` | `maintenance_technician` |

Admin Dashboard 9 modül sunar: **Satış Analizi, Performans, Stok Kontrol, Depolar, Kampanyalar, Ürünler, Kullanıcılar, Raporlar, Bildirimler**.

---

## API Modülleri

Tüm API endpoint'leri **`/api`** prefix'i ile sunulur (Kubernetes ingress gereği).

### 🔐 Authentication – `/api/auth`
- `POST /login` – JWT ile giriş
- `GET /me` – Oturum açmış kullanıcı
- `/customer/*` – Müşteri auth (ek akış)

### 👥 Users – `/api/users`
- `GET /` – Kullanıcı listesi (admin)
- `POST /create` – Yeni kullanıcı (admin)
- `PUT /{id}` – Güncelleme
- `PUT /{id}/password` – Şifre değiştirme
- `DELETE /{id}` – Soft delete (deaktif)
- `POST /{id}/activate` – Reaktive
- `DELETE /{id}/permanent` – Hard delete

### 📦 Products – `/api/products`
- CRUD + kategori filtreleme + lookup

### 📄 Invoices – `/api/invoices`
- `POST /upload` – HTML/SED fatura upload
- `POST /manual-entry` – Manuel fatura (otomatik müşteri/ürün oluşturur)
- `GET /all/list` – Tüm faturalar (admin/muhasebe)
- `GET /my-invoices` – Müşteri kendi faturaları
- `GET /{id}` – Fatura detayı
- `/customers/lookup/{tax_id}` – Vergi no ile müşteri ara

### 🏛️ GİB – `/api/gib`
- CSV/Excel toplu import
- `/api/gib/live/*` – Canlı e-fatura akışı

### 🍑 ŞEFTALİ – `/api/seftali`
- `/smart-orders` – akıllı sipariş önerileri
- `/stock` – plasiyer stoğu
- `/customers` – plasiyer müşterileri
- `/orders` – plasiyer sipariş akışı
- `/deliveries` – teslimat
- `/campaigns` – kampanya listeleme
- `/admin/*` – ŞEFTALİ admin operasyonu

### 📊 Analytics, Warehouses, Campaigns, Consumption, Production
Bu endpoint'ler `server.py` içinde doğrudan eklenmiş olup sırasıyla aşağıdaki prefix'lerde sunulur:

- `/api/analytics/dashboard-stats`, `/sales`, `/performance`, `/stock`
- `/api/warehouses` – CRUD + stats
- `/api/campaigns` – CRUD + activate
- `/api/customer-consumption/invoice-based/*` – fatura bazlı tüketim
- `/api/consumption-periods/*` – periyodik tüketim & YoY
- `/api/production/*` – lines, bom, plans, orders, quality-control
- `/api/notifications` – list, unread-count, create
- `/api/sales-routes` – haftalık müşteri rotası

> Tam endpoint listesi için: http://localhost:8001/docs (Swagger)

---

## Seed Scriptleri

| Script | Açıklama |
|--------|---------|
| `reset_demo_accounts.py` | Tüm demo kullanıcıları sıfırlar |
| `seed_seftali_data.py` | ŞEFTALİ modülü (ürün, müşteri, teslimat) |
| `seed_sales_agents_data.py` | 18 müşteri + 3 plasiyer + rotalar |
| `seed_weekly_orders.py` | Plasiyer1 için 120 haftalık sipariş |
| `seed_warehouses.py` | 7+ depo |
| `seed_warehouse_data.py` | Depo stok verileri |
| `seed_advanced_campaigns.py` | 5 gelişmiş kampanya |
| `seed_campaigns.py` | Temel kampanyalar |
| `seed_production_data.py` | Üretim hatları, BOM, planlar, emirler |
| `seed_maintenance_data.py` | Bakım görevleri |
| `seed_accounting_users.py` | Muhasebe kullanıcıları |
| `seed_20_products_orders.py` | 20 ürün + örnek siparişler |
| `seed_sample_products.py` | Örnek ürün kataloğu |
| `seed_phase2_data.py` | Phase-2 toplu data |
| `seed_complete_system.py` | Bütünsel demo seed |
| `seed_seftali_data.py` | ŞEFTALİ demo seed |
| `import_ailem_market.py` / `import_ailem_market_67.py` | Gerçek müşteri excel import |
| `import_excel_consumption.py` | Excel tüketim verisi import |
| `bulk_calculate_consumption.py` | Mevcut faturalardan tüketim toplu hesaplama |
| `create_consumption_history.py` | Geçmiş tüketim kayıtları oluştur |
| `cleanup_users.py` | Kullanıcı temizleme |
| `clean_database.py` | Tüm collection'ları temizler (dikkatli!) |

---

## Test

### Backend contract testleri

```bash
cd backend
pytest -q \
  tests/test_smart_order_contracts.py \
  tests/test_warehouse_draft.py \
  tests/test_plasiyer_stock_contracts.py \
  tests/test_plasiyer_customer_contracts.py \
  tests/test_plasiyer_orders_contracts.py \
  tests/test_plasiyer_deliveries_contracts.py \
  tests/test_plasiyer_campaigns_contracts.py
```

Bu testler route-split ve naming migration batch'lerinde:
- Mevcut endpoint davranışını korur
- Response shape değişikliklerini yakalar
- Güvenli incremental refactor yapılmasını sağlar

### Manuel API doğrulama

```bash
# Login
curl -X POST http://localhost:8001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Fatura listesi
curl http://localhost:8001/api/invoices/all/list \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Sorun Giderme

### Backend açılmıyorsa

```bash
# Eksik paket: bs4, lxml
pip install beautifulsoup4 lxml

# Logları incele
tail -n 50 /var/log/supervisor/backend.err.log
sudo supervisorctl restart backend
```

### Frontend açılmıyorsa (`craco: not found`)

```bash
cd frontend
yarn install
sudo supervisorctl restart frontend
```

### MongoDB bağlantı sorunu

- MongoDB servisinin çalıştığını doğrulayın: `sudo supervisorctl status mongodb`
- `backend/.env` içindeki `MONGO_URL` değerini kontrol edin
- DB boşsa `python reset_demo_accounts.py` ile seed edin

### Login "Invalid username or password"

Veritabanı boş olabilir:

```bash
cd backend
python reset_demo_accounts.py
```

### "craco start" bir kez çalışıyor, yeniden başlatınca hata veriyor

Port kilitli kalmış olabilir:

```bash
sudo supervisorctl stop frontend
fuser -k 3000/tcp 2>/dev/null
sudo supervisorctl start frontend
```

### CORS hatası

`backend/.env` içindeki `CORS_ORIGINS` değerine frontend URL'ini ekleyin:

```env
CORS_ORIGINS="http://localhost:3000,https://your-domain.com"
```

### Fatura parse sorunları

- SED formatı için `services/invoice_service.py` içindeki `_parse_sed_invoice` fonksiyonu kullanılır.
- Müşteri adı ikinci `<b>` span'dan alınır (ilki "SAYIN" olur).
- Türkçe karakter sorununda HTML charset'i `utf-8` olduğundan emin olun.

---

## Güvenlik Notları

- `SECRET_KEY` production'da mutlaka değiştirilmelidir
- `DEFAULT_CUSTOMER_PASSWORD` otomatik oluşturulan müşteri hesapları için kullanılır, production'da kapatın veya random hale getirin
- JWT token süresi default **30 gün** (istenirse `auth_routes.py` üzerinden kısaltın)
- Password hashing: `bcrypt` (via passlib)
- Rol doğrulaması: `middleware/auth.py` içinde `require_role([UserRole.X])` decorator'ı ile

---

## Geliştirme Prensipleri

- **Domain-based routing**: smart-orders, stock, customers, orders, deliveries, campaigns ayrımı
- **Minimal safe refactors**: küçük, geri alınabilir değişiklikler
- **Backward compatibility**: legacy endpoint'ler (örn. `warehouse-draft`) korunur
- **Contract-first changes**: davranış testle dondurulur, sonra taşıma yapılır
- **Clarity over flexibility**: sade ve anlaşılır yapı öncelikli
- **UUID primary keys** (MongoDB ObjectId asla response'a sızmaz)
- **Async-first**: motor (async MongoDB) ile tüm DB işlemleri

---

## Yol Haritası (Özet)

- [ ] Repository layer extraction (domain bazlı)
- [ ] Frontend feature-based split (pages → feature modülleri)
- [ ] Role-based route guards konsolidasyonu
- [ ] E-fatura dış servis adapter'ının genişletilmesi
- [ ] Mobil (PWA) plasiyer deneyimi
- [ ] Real-time notification (WebSocket)

Detaylı plan: [ROADMAP.md](./ROADMAP.md)

---

## Katkı

Katkı rehberi: [CONTRIBUTING.md](./CONTRIBUTING.md)

- Küçük PR'lar tercih edilir
- Yeni endpoint eklerken ilgili domain altına koyun (`routes/seftali/` veya uygun yeri)
- Model değişikliği yapıyorsanız `DATABASE_SCHEMA.md` dosyasını güncelleyin
- Tüm yeni feature'lar için en az bir contract test yazın

---

## Lisans

MIT
