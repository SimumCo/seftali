# ŞEFTALİ Dağıtım Yönetim Sistemi PRD

## Son Güncelleme: 1 Nisan 2026

## Proje Özeti
Yoğurt/ayran dağıtımı yapan bir firmada müşterilerin tüketimini teslimat bazlı hesaplayan ve rota gününe göre sipariş taslağı oluşturan **deterministik** bir sistem.

---

## ✅ SON GÜNCELLEME - FRONTEND DRAFT CUSTOMER MANAGEMENT BATCH (16 Nisan 2026)

### Yeni Özellikler

#### Plasiyer Customers Alanı İçinde Draft Customer Yönetimi
- ✅ Yeni bileşen eklendi: `/app/frontend/src/components/plasiyer/DraftCustomersManager.jsx`
- ✅ `CustomersPage` içine iki alt görünüm eklendi:
  - `Aktif Müşteriler`
  - `Draft Müşteriler`
- ✅ Yeni sidebar item eklenmedi
- ✅ Draft customer listesi gerçek backend endpoint'i ile bağlandı:
  - `GET /api/draft-customers?salespersonId=`
- ✅ Approve modal/form gerçek backend endpoint'i ile bağlandı:
  - `POST /api/draft-customers/:id/approve`
- ✅ `services/api.js` içine `customerOnboardingAPI` eklendi

#### UI Davranışı
- ✅ loading / empty / error state eklendi
- ✅ Approve başarılı olunca satır listeden kaldırılıyor
- ✅ Backend validation / duplicate / permission hataları kullanıcıya toast ile gösteriliyor
- ✅ Mevcut aktif müşteri görünümü korunuyor

#### Doğrulama
- ✅ Frontend lint temiz geçti
- ✅ Testing agent ile doğrulandı: `/app/test_reports/iteration_11.json`
- ✅ Draft customer frontend akışı %100 geçti
- ✅ Testing agent backend tarafında da 9/9 ilgili test geçti

---

## ✅ SON GÜNCELLEME - FRONTEND CUSTOMER AUTH BATCH (16 Nisan 2026)

### Yeni Özellikler

#### Customer Auth UI
- ✅ Yeni sayfalar eklendi:
  - `/app/frontend/src/pages/CustomerLoginPage.jsx`
  - `/app/frontend/src/pages/CustomerChangePasswordPage.jsx`
- ✅ Yeni route'lar eklendi:
  - `/customer-login`
  - `/customer/change-password`
- ✅ Mevcut `/login` ekranına dokunulmadı
- ✅ Customer auth akışı gerçek backend endpointleriyle bağlandı:
  - `POST /api/auth/customer/login`
  - `POST /api/auth/customer/change-password`

#### Session ve Guard Entegrasyonu
- ✅ `AuthContext` customer session desteği ile genişletildi
- ✅ `api.js` customer token gönderimini destekleyecek şekilde güncellendi
- ✅ `PASSWORD_CHANGE_REQUIRED` cevabı merkezi olarak yakalanıp `/customer/change-password` ekranına yönlendiriliyor
- ✅ Customer logout akışı `/customer-login` rotasına uyumlu hale getirildi
- ✅ Employee login akışı korunuyor

#### Doğrulama
- ✅ Frontend lint temiz geçti
- ✅ Testing agent ile doğrulandı: `/app/test_reports/iteration_10.json`
- ✅ Customer auth frontend akışı %100 geçti
- ✅ Testing agent `api.js` içinde 401 login-page redirect hatasını düzeltti

---

## ✅ SON GÜNCELLEME - CODE QUALITY BATCH Q2 (17 Nisan 2026)

### Yeni Özellikler

#### Hook / Stale Closure Hardening
- ✅ `CustomerDashboard.js` içindeki dashboard/stat yükleme akışları `useCallback` bağımlılık karmaşasından çıkarılıp effect-local async pattern'e taşındı
- ✅ `PlasiyerDashboardShell.jsx` ürün yükleme akışı effect-local async pattern ile sadeleştirildi
- ✅ Amaç: stale closure riskini azaltmak ve dependency yönetimini daha deterministik hale getirmek
- ✅ `OrderManagement.js` tarafındaki sessiz veri yok catch'leri debug log ile netleştirildi

#### Doğrulama
- ✅ Frontend lint temiz geçti
- ✅ Testing agent ile doğrulandı: `/app/test_reports/iteration_13.json`
- ✅ Hook cleanup sonrası frontend %100 geçti
- ✅ Hem plasiyer hem customer dashboard tarafında regresyon bulunmadı

#### Audit Sonucu
- ✅ Testing agent raporuna göre mevcut hedef dosyalarda artık anlamlı stale closure sorunu kalmadı
- ⚠ Recharts boyut warning'i küçük/cosmetic olarak sürüyor, işlevsel bug değil

---

## ✅ SON GÜNCELLEME - CODE QUALITY BATCH Q1 (16 Nisan 2026)

### Yeni Özellikler

#### Güvenli Secret Yönetimi
- ✅ `utils/auth.py` içindeki hardcoded `SECRET_KEY` fallback kaldırıldı
- ✅ `services/gib_import/constants.py` içindeki `DEFAULT_CUSTOMER_PASSWORD` env-backed hale getirildi
- ✅ `backend/.env` içine `DEFAULT_CUSTOMER_PASSWORD` tanımı eklendi
- ✅ Customer auth test dosyaları artık default customer password değerini env üzerinden okuyor

#### Düşük Riskli Frontend Error Handling Temizliği
- ✅ `CustomerDashboard.js` içindeki silent catch blokları log + kullanıcı dostu hata mesajı ile güncellendi
- ✅ `PlasiyerDashboardShell.jsx` ürün yükleme catch bloğu log + toast ile güncellendi
- ✅ `components/customer/OrderManagement.js` içindeki boş catch blokları debug log ile temizlendi

#### Doğrulama
- ✅ Python/JS lint temiz geçti
- ✅ Customer auth testleri tekrar çalıştırıldı: `25 passed, 4 skipped`
- ✅ Tüm mevcut backend test seti tekrar çalıştırıldı: toplam `85/85` geçti

#### Bilinçli Olarak Ertelenenler
- ⚠ `localStorage -> httpOnly cookie` geçişi bu batch'te yapılmadı; ayrı auth migration batch'i gerektirir
- ⚠ Hook dependency / stale closure düzeltmeleri ayrı batch'e bırakıldı
- ⚠ Büyük component/script refactor'ları bu batch kapsamına alınmadı

---

## ✅ SON GÜNCELLEME - FRONTEND SMART ORDER DEBUG UI BATCH (16 Nisan 2026)

### Yeni Özellikler

#### Plasiyer Smart Orders Debug Görünümü
- ✅ `WarehouseDraftPage.js` ürün kartları genişletildi
- ✅ Her ürün kartına mini hızlı bakış alanı eklendi:
  - Günlük tüketim
  - Trend
  - Son öneri
- ✅ `Detayları Gör` ile açılan debug panel eklendi
- ✅ Panel bölümleri:
  - Tüketim
  - Rota
  - Multiplier
  - Hesap
  - SKT
- ✅ `excluded_items` varsa üstte özet badge/panel gösterimi eklendi
- ✅ Yeni endpoint yazılmadı; mevcut `/api/seftali/sales/warehouse-draft` response'u kullanıldı
- ✅ Null-safe fallback label'lar eklendi:
  - `Veri yok`
  - `Yetersiz veri`
  - `Hesaplanamadı`

#### Doğrulama
- ✅ Frontend lint temiz geçti
- ✅ Testing agent ile doğrulandı: `/app/test_reports/iteration_12.json`
- ✅ Debug UI batch frontend %100 geçti
- ✅ Submit button ve mevcut Smart Orders akışı bozulmadı

---

## ✅ SON GÜNCELLEME - E-FATURA BACKEND BATCH (18 Nisan 2026)

### Yeni Özellikler

#### Minimum Production-Grade e-Fatura Modülü
- ✅ Yeni servis paketi eklendi: `/app/backend/services/efatura/`
- ✅ Yeni route dosyası eklendi: `/app/backend/routes/invoices_routes.py`
- ✅ Yeni repository eklendi: `/app/backend/repositories/efatura_repository.py`
- ✅ Minimum UBL üretimi eklendi: `/app/backend/services/efatura/ubl_builder.py`
- ✅ Env-configurable provider adapter eklendi: `/app/backend/services/efatura/provider_adapter.py`
- ✅ Queue/polling için basit command eklendi: `/app/backend/scripts/dev/poll_einvoice_statuses.py`
- ✅ Manuel smoke test rehberi eklendi: `/app/docs/efatura-smoke-test.md`

#### Yeni Endpointler
- ✅ `POST /api/invoices/test-smoke`
- ✅ `POST /api/invoices`
- ✅ `GET /api/invoices/{id}`
- ✅ `GET /api/invoices/{id}/status`
- ✅ `POST /api/invoices/{id}/refresh-status`

#### Teknik Davranış
- ✅ Internal status modeli uygulandı:
  - `draft`
  - `queued`
  - `processing`
  - `sent`
  - `failed`
- ✅ Create çağrısında başarılı HTTP cevap doğrudan `sent` sayılmıyor
- ✅ Status refresh ile `sent/failed` geçişi yapılıyor
- ✅ Provider request/response logları `invoice_provider_logs` collection'ında tutuluyor
- ✅ `x-api-key`, provider base URL ve path'ler env-configurable
- ✅ Mock provider uydurulmadı; gerçek adapter iskeleti kuruldu

#### Doğrulama
- ✅ Yeni e-Fatura test dosyası eklendi: `/app/backend/tests/test_efatura_module.py`
- ✅ e-Fatura testleri geçti: `5/5`
- ✅ Tüm mevcut backend test seti tekrar çalıştırıldı: toplam `99/99` geçti
- ⚠ Gerçek provider success-case henüz gerçek API key ve gerçek path olmadan doğrulanmadı

---

## ✅ SON GÜNCELLEME - CODE QUALITY BATCH Q3-A (18 Nisan 2026)

### Yeni Özellikler

#### Güvenli Quality Fix Subset
- ✅ `test_plasiyer_customers.py` içindeki hardcoded plasiyer şifresi env-backed hale getirildi
- ✅ `backend/.env` içine test credential env alanları eklendi:
  - `PLASIYER_TEST_USERNAME`
  - `PLASIYER_TEST_PASSWORD`
- ✅ `SalesAgentCustomers.js` içinde pahalı grouping/sort işlemleri `useMemo` ile sabitlendi
- ✅ `RouteOrderPage.js` içinde pahalı sort/filter işlemleri `useMemo` ile sabitlendi
- ✅ `ProductionOrderList.js` içinde pahalı seçim/filter listeleri `useMemo` ile sabitlendi
- ✅ Bazı kritik `index as key` kullanımları stable/composite key'lere çevrildi:
  - `CustomerCard.js`
  - `AdminDashboard.js`

#### Bilinçli Kapsam Dışı Bırakılanlar
- ⚠ `localStorage -> httpOnly cookie` auth migration yapılmadı
- ⚠ büyük component parçalama yapılmadı
- ⚠ geniş hook dependency sweep yapılmadı
- ⚠ script complexity refactor'ları yapılmadı
- ⚠ raporda belirtilen mutable default / undefined variable bulguları bu batchte somut olarak doğrulanmadığı için agresif değişiklik yapılmadı

#### Doğrulama
- ✅ Python/JS lint temiz geçti
- ✅ `test_plasiyer_customers.py` geçti: `10/10`
- ✅ Tüm mevcut backend test seti tekrar çalıştırıldı: toplam `104/104` geçti

---

## ✅ SON GÜNCELLEME - GIB LOGIN ERROR CLASSIFICATION FIX (18 Nisan 2026)

### Root Cause
- ✅ Yanlış kullanıcı adı/şifre senaryosunda login sonucu tekrar login sayfasına düşüyordu
- ✅ Önceki implementasyon, yalnızca basit hata metni tarayıp ardından `success marker` bulamazsa doğrudan `portal_layout_changed` veriyordu
- ✅ Bu yüzden bazı gerçek `invalid_credentials` durumları yanlış sınıflanıyordu

### Uygulanan Düzeltme
- ✅ `gib_client.py` içinde login sınıflandırma mantığı daraltıldı ve güvenli hale getirildi
- ✅ `invalid_credentials` artık yalnızca şu koşullarda dönüyor:
  - login formu tekrar mevcut
  - success marker yok
  - ve bilinen başarısız giriş ipuçları var
- ✅ `portal_layout_changed` artık yalnızca login sonucu güvenli biçimde sınıflandırılamadığında dönüyor
- ✅ login-page repeat tek başına `invalid_credentials` sayılmıyor

### Test ve Doğrulama
- ✅ Yeni test dosyası eklendi: `/app/backend/tests/test_gib_client_login_classification.py`
- ✅ Doğrulanan senaryolar:
  - invalid credentials HTML
  - login page repeat without failure clue
- ✅ İlgili live suite geçti: `8/8`
- ✅ Tüm mevcut backend test seti tekrar çalıştırıldı: toplam `94/94` geçti

---

## ✅ SON GÜNCELLEME - FRONTEND GIB CONNECTION UI BATCH (18 Nisan 2026)

### Yeni Özellikler

#### Plasiyer GİB Bağlantı Ekranı
- ✅ Yeni sayfa eklendi: `/app/frontend/src/pages/GibConnectionPage.jsx`
- ✅ Yeni servis eklendi: `/app/frontend/src/services/gibApi.js`
- ✅ Plasiyer sidebar'a yeni item eklendi: `GİB Bağlantı`
- ✅ Yeni route desteklendi: `/plasiyer/gib-connection`
- ✅ Sayfa açılışında otomatik `GET /api/gib/live/status` çağrısı yapılıyor
- ✅ Canlı endpoint entegrasyonları bağlandı:
  - `POST /api/gib/live/connect`
  - `GET /api/gib/live/status`
  - `POST /api/gib/live/import/start`
  - `POST /api/gib/live/disconnect`
- ✅ Hazır tarih aralığı seçenekleri eklendi:
  - Son 7 gün
  - Son 30 gün
  - Son 90 gün
  - Özel aralık
- ✅ İçe aktarma sonrası küçük sonuç özeti kartı eklendi:
  - işlenen fatura sayısı
  - atlanan kayıt sayısı
  - parse hata sayısı

#### UX / Güvenlik
- ✅ Credential'lar sadece local state'te tutuluyor
- ✅ Şifre input'u maskeli
- ✅ `connected / not_connected / expired` badge durumları görselleştirildi
- ✅ Error code → kullanıcı dostu Türkçe mesaj eşlemesi eklendi
- ✅ Direct deep-link sonrası login olunca hedef route'a geri dönme desteği eklendi
- ✅ `Faturaları Çek` bağlı değilken pasif hale getirildi

#### Doğrulama
- ✅ Frontend lint temiz geçti
- ✅ Testing agent ile doğrulandı: `/app/test_reports/iteration_14.json`
- ✅ Backend GİB live endpoint doğrulaması geçti: `12/12`
- ✅ Frontend GİB Bağlantı ekranı doğrulaması geçti: `%100`

---

## ✅ SON GÜNCELLEME - GIB LIVE ADAPTER BATCH (17 Nisan 2026)

### Yeni Özellikler

#### Adapter Mimarisi
- ✅ Yeni adapter tabanlı yapı eklendi:
  - `MockGibAdapter`
  - `LiveGibAdapter`
- ✅ Import service artık mode bazlı adapter seçebiliyor
- ✅ Mevcut mock import akışı korunuyor

#### Canlı GİB Login / Session Katmanı
- ✅ Yeni dosyalar eklendi:
  - `/app/backend/services/gib_import/live_gib_adapter.py`
  - `/app/backend/services/gib_import/session_manager.py`
  - `/app/backend/services/gib_import/gib_client.py`
  - `/app/backend/services/gib_import/errors.py`
- ✅ In-memory session ref yönetimi eklendi
- ✅ Status durumları netleştirildi:
  - `connected`
  - `expired`
  - `not_connected`
- ✅ Plain text credential/cookie persist edilmeden login/session akışı kuruldu

#### Yeni Endpointler
- ✅ `POST /api/gib/live/connect`
- ✅ `POST /api/gib/live/import/start`
- ✅ `GET /api/gib/live/status`
- ✅ `POST /api/gib/live/disconnect`

#### Observability / Job Alanları
- ✅ Import job güncellemeleri genişletildi:
  - `mode`
  - `parse_error_count`
  - `login_error_count`
  - `portal_changed`
  - `skipped_count`
  - `imported_invoice_count`
- ✅ `raw_ref.source = live_gib` desteği eklendi

#### Test ve Doğrulama
- ✅ Yeni test dosyası eklendi: `/app/backend/tests/test_live_gib_integration.py`
- ✅ Doğrulanan başlıklar:
  - login success
  - invalid credentials
  - session expired
  - parser integration
  - duplicate invoice protection
  - mock mode regression
  - live mode failure handling
- ✅ Tüm mevcut backend test seti tekrar çalıştırıldı: toplam `92/92` geçti

#### Açık Sınır
- ⚠ Canlı portal login başarı testi gerçek credential olmadan doğrulanmadı
- ⚠ Bu batchte gerçek GİB portal ile success-case smoke yapılmadı; integration-style mocked portal HTML ile doğrulandı

## ✅ SON GÜNCELLEME - TURKCELL CREATE PIPELINE ISOLATION TEST (20 Nisan 2026)

### İzole Deneme
- ✅ `provider_adapter.py` içinde yalnızca 3 alan değiştirildi:
  - `status=20` → `status=0`
  - `Accept: application/json`
  - `invoiceFile` content-type: `text/xml`
- ✅ Başka hiçbir alan değiştirilmeden gerçek provider üzerinde `POST /api/invoices/test-smoke` tekrar çalıştırıldı

### Sonuç
- ✅ HTTP status yine `400` döndü
- ✅ Provider payload yine generic internal hata verdi
- ✅ `Id` / `provider_invoice_id` yine oluşmadı
- ✅ Davranış anlamlı biçimde değişmedi; bu 3 alan ana blocker değil
- ✅ Ek olarak farklı API key ile gerçek smoke retry denendi; sonuç yine aynı generic `400` oldu (`traceId: 0f569d7ac784b669e2e01bd700fa452c`)

---

## ✅ SON GÜNCELLEME - END-TO-END GIB → DRAFT → SMART ORDERS BATCH (17 Nisan 2026)

### Yeni Özellikler

#### customers ↔ sf_customers Bridge
- ✅ `CustomerApprovalService` artık approve sonrası `sf_customers` bridge kaydı oluşturuyor
- ✅ Bridge duplicate üretmiyor; önce `customer_id`, sonra identity üzerinden mevcut kayıt kontrol ediliyor
- ✅ `route_plan` çözümü sırası eklendi:
  1. draft context
  2. salesperson context
  3. mevcut sf_customer context
  4. güvenli default `['MON', 'FRI']`

#### Customer Consumption Endpoint Modernizasyonu
- ✅ `GET /api/seftali/customer/daily-consumption` artık yeni collection'ları kullanıyor:
  - `customer_product_daily_consumptions`
  - `customer_product_consumptions`
- ✅ `GET /api/seftali/customer/daily-consumption/summary` de yeni aggregate verilerle uyumlu hale getirildi
- ✅ Backward-compatible alanlar korunurken additive alanlar eklendi:
  - `rate_mt_weighted`
  - `trend`
  - `confidence_score`
  - `last_quantity`
  - `last_invoice_date`
  - `estimated_depletion_days`

#### Yeni Smart Orders Endpointi
- ✅ Yeni endpoint eklendi: `GET /api/seftali/sales/smart-draft-v2`
- ✅ Bu endpoint aktif `sf_customers` üzerinden `DraftEngine.calculate()` çağırıyor
- ✅ Customer bazlı response + flattened `order_items` + `excluded_items` birlikte dönüyor
- ✅ Mevcut `/warehouse-draft` endpointine dokunulmadı

#### Frontend Smart Orders Entegrasyonu
- ✅ `WarehouseDraftPage.js` artık önce `smart-draft-v2` endpointini deniyor
- ✅ Hata durumunda güvenli rollout için `/warehouse-draft` fallback'i bırakıldı
- ✅ Yeni response shape frontend tarafında normalize edilip mevcut UI yapısına bağlandı
- ✅ `excluded_items` badge artık gerçek veriden beslenebiliyor

#### Kritik Ek Entegrasyon
- ✅ GİB import edilen invoice line'lar için deterministic `product_id` üretimi eklendi
- ✅ Import sırasında `products` + `product_aliases` kayıtları otomatik upsert edilerek consumption → draft zinciri kapatıldı

#### Doğrulama
- ✅ Yeni uçtan uca test eklendi: `/app/backend/tests/test_gib_to_smart_orders_pipeline.py`
- ✅ Bu test şu zinciri doğruluyor:
  - mock GİB import
  - draft customer oluşumu
  - approve
  - sf_customer bridge
  - invoice linking
  - consumption recalculation
  - `smart-draft-v2`
  - customer login + password change guard sonrası consumption erişimi
- ✅ Tüm mevcut backend test seti tekrar çalıştırıldı: toplam `86/86` geçti
- ✅ Frontend smoke doğrulaması yapıldı; Smart Orders ekranı artık yeni endpoint ile en az bir ürün ve excluded badge gösteriyor

---

## ✅ SON GÜNCELLEME - DRAFT ENGINE BATCH 12 (16 Nisan 2026)

### Yeni Özellikler

#### Abandon Rule + SKT Clamp
- ✅ `draft_engine.py` içine abandon rule eklendi
- ✅ `draft_engine.py` içine SKT clamp eklendi
- ✅ İşlem sırası güncellendi:
  1. `rate_base`
  2. `weekly_multiplier`
  3. `pre_clamp_need_qty`
  4. abandon kontrolü
  5. SKT clamp
  6. final qty
- ✅ Abandon olan ürünler draft listesinden çıkarılıyor ve `excluded_items` altında izleniyor
- ✅ Additive debug alanlar eklendi:
  - `abandoned`
  - `abandoned_reason`
  - `expected_depletion_days`
  - `days_since_last_delivery`
  - `pre_clamp_need_qty`
  - `final_need_qty`
  - `coverage_days`
  - `shelf_life_days`
  - `was_clamped`
  - `clamp_reason`
  - `max_safe_qty`
- ✅ `customer_routes.py` içindeki draft endpoint, `excluded_items` varlığında fallback'e düşmeyecek şekilde düzeltildi

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Yeni test dosyası eklendi: `/app/backend/tests/test_draft_engine_abandon_skt.py`
- ✅ Abandon/SKT testleri geçti: `7/7`
- ✅ Tüm mevcut backend test seti tekrar çalıştırıldı: toplam `85/85` geçti
- ✅ Canlı smoke doğrulaması yapıldı; örnek draft çıktısında clamp debug alanları doğrulandı

---

## ✅ SON GÜNCELLEME - DRAFT ENGINE BATCH 11 (16 Nisan 2026)

### Yeni Özellikler

#### Weekly Multiplier Lookup V2
- ✅ `draft_engine.py` içindeki weekly multiplier lookup fallback zinciri ile güncellendi
- ✅ Deterministic lookup sırası uygulandı:
  1. `(depot_id, segment_id, product_id, week_start)`
  2. `(segment_id, product_id, week_start)`
  3. `(product_id, week_start)`
  4. `default = 1.0`
- ✅ Belirsiz `depot_id` / `segment_id` durumlarında sessiz uydurma yapılmıyor; yalnızca alt fallback seviyesine iniliyor
- ✅ Draft response içine additive metadata eklendi:
  - `weekly_multiplier_source`

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Yeni multiplier lookup test dosyası eklendi: `/app/backend/tests/test_weekly_multiplier_lookup.py`
- ✅ Multiplier lookup testleri geçti: `5/5`
- ✅ Tüm mevcut backend test seti tekrar çalıştırıldı: toplam `78/78` geçti
- ✅ Canlı smoke doğrulaması yapıldı; örnek draft çıktısında:
  - `weekly_multiplier = 1.4`
  - `weekly_multiplier_source = depot_segment_product`
  - `rate_source = aggregate`

---

## ✅ SON GÜNCELLEME - DRAFT ENGINE BATCH 10 (16 Nisan 2026)

### Yeni Özellikler

#### Draft Engine Dual-Read Geçişi
- ✅ `draft_engine.py` dual-read mantığı ile güncellendi
- ✅ Yeni okuma önceliği eklendi:
  1. `customer_product_consumptions.rate_mt_weighted`
  2. fallback: `de_customer_product_state.rate_mt`
- ✅ Draft formülü güncellendi:
  - `need_qty = rate_base × weekly_multiplier × days_to_next_route`
- ✅ `supply_days` ana formülden çıkarıldı, metadata olarak korunuyor
- ✅ Additive response alanları eklendi:
  - `rate_source`
  - `rate_mt_weighted`
  - `confidence_score`
  - `trend`
  - `formula_version`
  - `days_to_next_route`
  - `expected_depletion_days`
  - `coverage_days`
- ✅ düşük güven durumu için `flags.low_confidence` eklendi

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Yeni dual-read test dosyası eklendi: `/app/backend/tests/test_draft_engine_dual_read.py`
- ✅ Dual-read testleri geçti: `5/5`
- ✅ Tüm mevcut backend test seti tekrar çalıştırıldı: toplam `73/73` geçti
- ✅ Canlı smoke doğrulaması yapıldı; draft response içinde `rate_source = aggregate` ve `formula_version = v2-dual-read` döndü

---

## ✅ SON GÜNCELLEME - GIB IMPORT BATCH 9 (16 Nisan 2026)

### Yeni Özellikler

#### Daily Consumption Timeseries (V2 Hazırlık)
- ✅ Yeni collection aktif hale getirildi: `customer_product_daily_consumptions`
- ✅ Bootstrap/index script güncellendi
- ✅ Unique index eklendi: `(customer_id, product_id, date)`
- ✅ `consumption_service.py` V2 hazırlığı ile genişletildi:
  - same-day merge
  - interval spread `(prev_date, curr_date]`
  - daily series full rebuild
  - weighted aggregate hesaplama
- ✅ `gib_import_repository.py` daily series CRUD/upsert metotlarıyla genişletildi
- ✅ `customer_product_consumptions` backward-compatible kalacak şekilde yeni alanlar yazılmaya başlandı:
  - `rate_mt_weighted`
  - `interval_count`
  - `skipped_interval_count`
  - `confidence_score`
  - `trend`
  - `invoice_count`
  - `normalization_source`
  - `last_calculated_at`

#### Batch 9 Davranışı
- ✅ daily series için full rebuild uygulanıyor
- ✅ same-day merge zorunlu hale geldi
- ✅ `prev_date` yazılmıyor, `curr_date` dahil ediliyor
- ✅ `daily_consumption` alanı backward compatibility için korunuyor
- ✅ `rate_mt_weighted` yeni canonical aggregate alanı olarak yazılıyor
- ✅ `draft_engine` bu batch'te özellikle değiştirilmedi

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Yeni test dosyası eklendi: `/app/backend/tests/test_customer_daily_consumption_timeseries.py`
- ✅ Yeni daily-series testleri geçti: `8/8`
- ✅ Tüm mevcut backend test seti tekrar çalıştırıldı: toplam `68/68` geçti
- ✅ Örnek smoke sonucu doğrulandı:
  - 1 Jan → 100, 11 Jan → 200
  - daily rows: `2–11 Jan` arası `10` kayıt
  - `daily_rate = 10`

---

## ✅ SON GÜNCELLEME - GIB IMPORT BATCH 8 (16 Nisan 2026)

### Yeni Özellikler

#### must_change_password Merkezi Guard
- ✅ Yeni middleware eklendi: `/app/backend/middleware/customer_password_change_guard.py`
- ✅ `server.py` içine merkezi guard olarak bağlandı
- ✅ `utils/auth.py` customer_users tokenlarını destekleyecek şekilde genişletildi
- ✅ `routes/seftali/customer_routes.py` yeni customer auth context için güvenli fallback aldı

#### Batch 8 Davranışı
- ✅ `must_change_password = true` customer user login olabiliyor
- ✅ ama `POST /api/auth/customer/change-password` dışında diğer endpointlere erişemiyor
- ✅ bloklanan isteklerde tam şu response dönüyor:
  - `{ "error": "PASSWORD_CHANGE_REQUIRED", "message": "Şifre değiştirmeniz gerekiyor" }`
- ✅ şifre değiştirildikten sonra erişim açılıyor
- ✅ `must_change_password = false` kullanıcı normal erişebiliyor
- ✅ kontrol merkezi middleware ile yapılıyor; endpoint bazlı hack eklenmedi

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Yeni test dosyası eklendi: `/app/backend/tests/test_customer_password_guard.py`
- ✅ Guard testleri geçti: `4/4`
- ✅ Tüm mevcut test seti tekrar çalıştırıldı: toplam `60/60` geçti
- ✅ Canlı smoke doğrulaması yapıldı; bloklama + change-password akışı doğrulandı

---

## ✅ SON GÜNCELLEME - GIB IMPORT BATCH 7 (16 Nisan 2026)

### Yeni Özellikler

#### Customer Change Password
- ✅ `CustomerAuthService` password change akışı ile genişletildi
- ✅ Yeni endpoint eklendi:
  - `POST /api/auth/customer/change-password`
- ✅ `contracts.py` içine `CustomerChangePasswordPayload` eklendi
- ✅ `GIBImportRepository` customer_user by id ve update metodlarıyla genişletildi

#### Batch 7 Davranışı
- ✅ endpoint token ile korunuyor
- ✅ authenticated customer user context token üzerinden doğrulanıyor
- ✅ `current_password` verify ediliyor
- ✅ `new_password` hashlenerek saklanıyor
- ✅ plain text şifre tutulmuyor
- ✅ yeni şifre eski ile aynıysa reddediliyor
- ✅ minimum güvenlik kontrolü var (uzunluk + harf + rakam)
- ✅ şifre değişince `must_change_password = false`
- ✅ `password_changed_at` güncelleniyor
- ✅ inactive user/customer işlem yapamıyor

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Yeni test dosyası eklendi: `/app/backend/tests/test_customer_change_password.py`
- ✅ Login + change-password testleri geçti: `12/12`
- ✅ Tüm mevcut test seti tekrar çalıştırıldı: toplam `56/56` geçti
- ✅ Canlı smoke doğrulaması yapıldı; login + change-password örnek response döndürüyor

---

## ✅ SON GÜNCELLEME - GIB IMPORT BATCH 6 (16 Nisan 2026)

### Yeni Özellikler

#### Customer Login
- ✅ Yeni servis eklendi: `/app/backend/services/gib_import/customer_auth_service.py`
- ✅ Yeni route eklendi: `/app/backend/routes/customer_auth_routes.py`
- ✅ Yeni endpoint eklendi:
  - `POST /api/auth/customer/login`
- ✅ `GIBImportRepository` login desteği için user update metoduyla genişletildi
- ✅ `contracts.py` içine `CustomerLoginPayload` eklendi

#### Batch 6 Davranışı
- ✅ login `customer_users` collection'ı üzerinden çalışıyor
- ✅ `username = tc_no / tax_number` mantığı destekleniyor
- ✅ hash verify kullanılıyor; plain text şifre karşılaştırması yok
- ✅ inactive user giriş yapamıyor
- ✅ inactive customer giriş yapamıyor
- ✅ `must_change_password` response'a dönüyor
- ✅ token mevcut auth yapısına uygun şekilde üretiliyor
- ✅ başarılı login sonrası `last_login_at` güncelleniyor

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Yeni customer login test dosyası eklendi: `/app/backend/tests/test_customer_auth_login.py`
- ✅ Customer login testleri geçti: `6/6`
- ✅ Tüm mevcut test seti tekrar çalıştırıldı: toplam `50/50` geçti
- ✅ Canlı smoke doğrulaması yapıldı; endpoint örnek response döndürüyor

---

## ✅ SON GÜNCELLEME - GIB IMPORT BATCH 5 (16 Nisan 2026)

### Yeni Özellikler

#### Customer Product Consumption
- ✅ `CustomerConsumptionService` gerçek çalışan hesaplama mantığı ile geliştirildi
- ✅ `GIBImportRepository` invoice line / alias / product consumption metodlarıyla genişletildi
- ✅ Yeni endpointler eklendi:
  - `POST /api/customers/{id}/recalculate-consption`
  - `GET /api/customers/{id}/consumption`

#### Batch 5 Davranışı
- ✅ sadece ilgili customer'a bağlı ve iptal edilmemiş faturalar kullanılıyor
- ✅ `invoice_lines` kayıtları product bazında gruplanıyor
- ✅ product normalizasyon mantığı:
  - önce `invoice_lines.product_id`
  - yoksa `product_aliases.normalized_alias`
  - eşleşmezse skip
- ✅ günlük tüketim hesabı interval-average yaklaşımı ile çalışıyor:
  - her ardışık fatura aralığı için `previous_quantity / day_diff`
  - tüm geçerli interval rate'lerin ortalaması `daily_consumption`
- ✅ tek fatura varsa `daily_consumption = null`
- ✅ `day_diff <= 0` aralıkları skip ediliyor
- ✅ `quantity <= 0` kayıtları skip ediliyor
- ✅ `customer_id + product_id` bazında upsert ile idempotent çalışıyor
- ✅ `average_order_quantity`, `last_invoice_date`, `last_quantity` alanları yazılıyor

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Yeni consumption test dosyası eklendi: `/app/backend/tests/test_customer_consumption.py`
- ✅ Consumption testleri geçti: `6/6`
- ✅ Tüm mevcut test seti tekrar çalıştırıldı: toplam `44/44` geçti
- ✅ Canlı smoke doğrulaması yapıldı; iki endpoint örnek response döndürüyor

---

## ✅ SON GÜNCELLEME - GIB IMPORT BATCH 4 (16 Nisan 2026)

### Yeni Özellikler

#### Historical Invoice Linking
- ✅ `InvoiceLinkService` gerçek çalışan linking mantığı ile geliştirildi
- ✅ `GIBImportRepository` invoice linking için yeni repository metodlarıyla genişletildi
- ✅ Yeni endpoint eklendi:
  - `POST /api/customers/{id}/link-invoices`

#### Batch 4 Davranışı
- ✅ customer kimliği çözülüyor:
  - önce `tc_no`
  - yoksa `tax_no`
  - yoksa `identity_number`
- ✅ customer kimliği yoksa hata dönüyor
- ✅ sadece aynı salesperson içindeki faturalar taranıyor
- ✅ sadece aynı identity'ye sahip faturalar değerlendiriliyor
- ✅ `customer_id` boş olan faturalar ilgili customer'a bağlanıyor
- ✅ aynı customer'a zaten bağlı faturalar skip ediliyor
- ✅ farklı customer'a bağlı faturalar overwrite edilmiyor, conflict sayılıyor
- ✅ `draft_customer_id` korunuyor; audit lineage bozulmuyor
- ✅ response içinde `linked_count`, `skipped_count`, `conflict_count` dönüyor
- ✅ işlem idempotent çalışıyor
- ✅ transaction desteklenirse transaction kullanılıyor; desteklenmiyorsa güvenli fallback ile devam ediliyor

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Yeni linking test dosyası eklendi: `/app/backend/tests/test_invoice_linking.py`
- ✅ Linking testleri geçti: `5/5`
- ✅ Tüm mevcut test seti tekrar çalıştırıldı: toplam `38/38` geçti
- ✅ Canlı smoke doğrulaması yapıldı; endpoint örnek response döndürüyor

---

## ✅ SON GÜNCELLEME - GIB IMPORT BATCH 3 (16 Nisan 2026)

### Yeni Özellikler

#### Draft Customer Approval Akışı
- ✅ `CustomerApprovalService` gerçek çalışan approval mantığı ile geliştirildi
- ✅ `GIBImportRepository` customer / customer_user / draft update metodlarıyla genişletildi
- ✅ Yeni endpoint eklendi:
  - `POST /api/draft-customers/{id}/approve`
- ✅ Endpoint `DraftCustomerApprovePayload` ile validate ediliyor

#### Batch 3 Davranışı
- ✅ Draft customer bulunamazsa `404`
- ✅ `tc_no` / `tax_number` / `identity_number` yoksa `400`
- ✅ `username = tc_no || tax_number`
- ✅ password `123123` olarak **hashlenmiş** saklanıyor
- ✅ `must_change_password = true`
- ✅ mevcut customer varsa yeniden customer oluşturmuyor
- ✅ mevcut username varsa mevcut user tekrar kullanılıyor
- ✅ draft status `approved` olarak güncelleniyor
- ✅ `approved_at`, `approved_customer_id`, `customer_user_id` alanları set ediliyor
- ✅ Mongo transaction desteklenirse transaction kullanılıyor; desteklenmiyorsa güvenli fallback ile devam ediliyor

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Approval endpoint için yeni test dosyası eklendi: `/app/backend/tests/test_draft_customer_approval.py`
- ✅ GİB import + approval testleri geçti: `5/5`
- ✅ Tüm mevcut test seti tekrar çalıştırıldı: toplam `33/33` geçti
- ✅ Canlı smoke doğrulaması yapıldı; endpoint örnek response döndürüyor

---

## ✅ SON GÜNCELLEME - GIB IMPORT BATCH 2 (16 Nisan 2026)

### Yeni Özellikler

#### Çalışan Mock Import Akışı
- ✅ Yeni route dosyası eklendi: `/app/backend/routes/gib_import_routes.py`
- ✅ Yeni repository eklendi: `/app/backend/repositories/gib_import_repository.py`
- ✅ Mock veri kaynağı eklendi: `/app/backend/services/gib_import/mock_dataset.py`
- ✅ HTML parse adapter eklendi: `/app/backend/services/gib_import/parser_adapter.py`
- ✅ `GIBImportService` gerçek çalışan ilk sürüme taşındı
- ✅ `DraftCustomerService` gerçek aggregation mantığı ile güncellendi
- ✅ Endpointler eklendi:
  - `POST /api/gib/import/start`
  - `GET /api/draft-customers?salespersonId=`

#### Batch 2 Davranışı
- ✅ Import job lifecycle çalışıyor: `pending -> running -> completed/failed`
- ✅ Mock dataset parse edilip normalize invoice modeli oluşturuluyor
- ✅ Mock dataset parse edilip normalize invoice_lines modeli oluşturuluyor
- ✅ Idempotent invoice upsert mantığı çalışıyor:
  - öncelik: `ettn`
  - fallback: `invoice_number + invoice_date + identity_number + salesperson_id`
- ✅ `draft_customers` aggregation çalışıyor:
  - grouping key: `tc_no || tax_no`
  - aynı salesperson içinde gruplanıyor
  - `invoice_count`, `first_invoice_date`, `last_invoice_date`, `total_amount` hesaplanıyor
- ✅ `raw_ref` + `raw_payload` alanları ile hafif raw import referansı saklanıyor

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Yeni GİB import contract testleri geçti
- ✅ Tüm mevcut test seti tekrar çalıştırıldı: toplam `30/30` geçti
- ✅ Mock sonuç doğrulandı:
  - imported invoices: `3`
  - skipped missing identity: `1`
  - draft customers: `2`

---

## ✅ SON GÜNCELLEME - GIB IMPORT BATCH 1 (15 Nisan 2026)

### Yeni Özellikler

#### Referans Repo Analizi ve İzole Modül İskeleti
- ✅ Referans repo analiz notu eklendi: `/app/docs/gib-import-architecture.md`
- ✅ Yeni izole backend modül paketi eklendi: `/app/backend/services/gib_import/`
- ✅ Aşağıdaki iskelet servisler oluşturuldu:
  - `import_service.py`
  - `draft_customer_service.py`
  - `customer_approval_service.py`
  - `invoice_link_service.py`
  - `consumption_service.py`
- ✅ Shared constants ve contracts eklendi:
  - `constants.py`
  - `contracts.py`

#### Mongo Collection + Index Bootstrap
- ✅ İdempotent bootstrap script eklendi: `/app/backend/scripts/dev/bootstrap_gib_import_collections.py`
- ✅ Şu collection yapıları için bootstrap/index tanımı kuruldu:
  - `salespersons`
  - `draft_customers`
  - `customers`
  - `customer_users`
  - `invoices`
  - `invoice_lines`
  - `products`
  - `product_aliases`
  - `customer_product_consumptions`
  - `gib_import_jobs`
- ✅ Unique / index kuralları tanımlandı:
  - `customer_users.username` unique
  - `invoices.ettn` unique+sparse
  - `customer_product_consumptions (customer_id, product_id)` unique
  - draft/customer identity compound indexleri

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ Bootstrap script art arda 2 kez çalıştırıldı
- ✅ Collection ve indexlerin oluştuğu doğrulandı
- ⚠️ Bu batch'te canlı GİB login/test bilinçli olarak yapılmadı

---

## ✅ SON GÜNCELLEME - FRONTEND REFACTOR BATCH F1 (15 Nisan 2026)

### Yeni Özellikler

#### Plasiyer Dashboard Shell Başlangıcı
- ✅ Yeni shell dosyası eklendi: `/app/frontend/src/pages/PlasiyerDashboardShell.jsx`
- ✅ Eski `/app/frontend/src/pages/PlasiyerDashboard.js` compatibility entry olarak korundu
- ✅ `App.js` import yolu değiştirilmeden çalışmaya devam ediyor
- ✅ Sidebar sadeleştirildi ve sadece şu öğeler bırakıldı:
  - Dashboard
  - Smart Orders
  - Customers
  - Orders
  - Stock
  - Deliveries
  - Campaigns
- ✅ Bu batch'te fetch logic, API layer ve component taşıma yapılmadı

#### Doğrulama
- ✅ Frontend lint temiz geçti
- ✅ Testing agent ile doğrulandı: `/app/test_reports/iteration_9.json`
- ✅ Shell + compatibility entry + sidebar sadeleşmesi başarılı bulundu
- ✅ OrdersPage içindeki React key warning'i ayrıca düzeltildi

---

## ✅ SON GÜNCELLEME - SAFE BACKEND MIGRATION BATCH 7 (1 Nisan 2026)

### Yeni Özellikler

#### Campaigns Duplicate Resolution
- ✅ Duplicate `GET /api/seftali/sales/campaigns` handler'ları karşılaştırıldı
- ✅ Contract karşılaştırması sonucu `valid_until` filtreli handler'ın mevcut canlı davranışla uyumsuz olduğu görüldü
- ✅ Bu nedenle canonical davranış olarak **status=active** tabanlı mevcut canlı listeleme seçildi
- ✅ Yeni servis katmanı eklendi: `/app/backend/services/seftali/campaign_service.py`
- ✅ Yeni route modülü eklendi: `/app/backend/routes/seftali/campaigns.py`
- ✅ Sadece canonical `GET /api/seftali/sales/campaigns` endpoint'i taşındı
- ✅ `POST /api/seftali/sales/campaigns/add-to-order` bu batch'te yerinde bırakıldı
- ✅ `sales_routes.py` içindeki duplicate iki `GET /campaigns` handler'ı kaldırıldı

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ `pytest` ile doğrulandı: toplam `28/28` geçti
- ✅ Canlı smoke doğrulaması yapıldı; `GET /api/seftali/sales/campaigns` aynı response shape ile çalışıyor
- ✅ Kök `README.md` güncellendi; mevcut backend modül ayrışması ve çalışma/test komutları belgelendi
- ✅ Yeni minimal contract test eklendi: `/app/backend/tests/test_plasiyer_campaigns_contracts.py`

---

## ✅ SON GÜNCELLEME - CAMPAIGNS OWNERSHIP AUDIT BATCH (1 Nisan 2026)

### Audit Sonucu

#### sales_routes.py İçinde Kalan Campaign Endpointleri
- ✅ `GET /api/seftali/sales/campaigns` (ilk handler) → **legacy duplicate**
  - Neden burada: eski basit kampanya listeleme handler'ı
  - Şimdilik kalsın mı: **Evet**
  - İleride ne olmalı: kaldırılmalı veya tek canonical handler'a indirilmeli
  - Hedef modül: `backend/routes/seftali/campaigns.py`

- ✅ `GET /api/seftali/sales/campaigns` (ikinci handler) → **campaign-owned**
  - Neden burada: daha güçlü filtreleme (`valid_until`) ile aktif kampanyaları döndürüyor
  - Şimdilik kalsın mı: **Evet**
  - İleride ne olmalı: campaigns modülüne taşınmalı ve canonical GET handler olmalı
  - Hedef modül: `backend/routes/seftali/campaigns.py`

- ✅ `POST /api/seftali/sales/campaigns/add-to-order` → **ambiguous**
  - Neden burada: campaign + working_copy + müşteri sipariş aksiyonu arasında kesişim var
  - Şimdilik kalsın mı: **Evet**
  - İleride ne olmalı: ownership netleştikten sonra campaigns modülüne veya order-actions modülüne taşınmalı
  - Hedef modül: öncelikli aday `backend/routes/seftali/campaigns.py`

#### Duplicate / Legacy Bulguları
- ✅ `GET /api/seftali/sales/campaigns` için iki ayrı handler mevcut
- ✅ Bu durum legacy birikim göstergesi; davranışı değiştirmemek için bu batch'te müdahale edilmedi
- ✅ Güvenli sonraki adım: sadece campaigns alanı için küçük bir façade + route split batch'i

#### Sonraki Güvenli Batch Önerisi
- ✅ Yeni batch önerisi: `backend/routes/seftali/campaigns.py`
- Önerilen kapsam:
  - önce ince `campaign_service.py` façade eklemek
  - ardından iki `GET /campaigns` handler'ı tek canonical handler etrafında toplamak
  - `POST /campaigns/add-to-order` ownership'i netse aynı batch'te taşımak; net değilse sonraya bırakmak

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ `pytest` ile doğrulandı: toplam `27/27` geçti

---

## ✅ SON GÜNCELLEME - SAFE BACKEND MIGRATION BATCH 6 (1 Nisan 2026)

### Yeni Özellikler

#### Deliveries Route Ayrıştırması
- ✅ Yeni servis katmanı eklendi: `/app/backend/services/seftali/delivery_service.py`
- ✅ Yeni route modülü eklendi: `/app/backend/routes/seftali/deliveries.py`
- ✅ Sadece şu net deliveries endpointler `sales_routes.py` içinden taşındı:
  - `POST /api/seftali/sales/deliveries`
  - `GET /api/seftali/sales/deliveries`
- ✅ Router register güncellendi: `routes/seftali/__init__.py`
- ✅ Aynı batch içinde taşınan delivery handler'ları `sales_routes.py` içinden kaldırıldı; duplicate route riski oluşmadı
- ✅ Endpoint path'leri, response formatı ve iş mantığı değiştirilmedi
- ✅ Bu batch sonunda `sales_routes.py` içindeki artık kullanılmayan deliveries schema/import kalıntıları temizlendi

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ `pytest` ile doğrulandı: toplam `27/27` geçti
- ✅ Canlı smoke doğrulaması yapıldı; `GET/POST /api/seftali/sales/deliveries` aynı response shape ile çalışıyor
- ✅ Yeni minimal contract test eklendi: `/app/backend/tests/test_plasiyer_deliveries_contracts.py`

---

## ✅ SON GÜNCELLEME - SALES_ROUTES OWNERSHIP AUDIT BATCH (1 Nisan 2026)

### Audit Sonucu

#### sales_routes.py İçinde Kalan Endpointler
- ✅ `POST /api/seftali/sales/deliveries` → **deliveries**
  - Neden burada: teslimat route'ları henüz ayrıştırılmadı
  - Şimdilik kalsın mı: **Evet**
  - İleride taşınmalı mı: **Evet**
  - Hedef modül: `backend/routes/seftali/deliveries.py`

- ✅ `GET /api/seftali/sales/deliveries` → **deliveries**
  - Neden burada: teslimat listeleme hâlâ legacy sales modülünde
  - Şimdilik kalsın mı: **Evet**
  - İleride taşınmalı mı: **Evet**
  - Hedef modül: `backend/routes/seftali/deliveries.py`

- ✅ `PATCH /api/seftali/sales/customers/{customer_id}` → **ambiguous**
  - Neden burada: müşteri güncelleme endpoint'i draft recalculation tetikliyor ve customer/domain ownership sınırı tam net değil
  - Şimdilik kalsın mı: **Evet**
  - İleride taşınmalı mı: **Muhtemelen**
  - Hedef modül: `backend/routes/seftali/customers.py` veya ayrı `customer_admin_actions.py`

- ✅ `GET /api/seftali/sales/products` → **other**
  - Neden burada: plasiyer UI destek endpoint'i olarak kullanılıyor, ownership net değil
  - Şimdilik kalsın mı: **Evet**
  - İleride taşınmalı mı: **Evet**
  - Hedef modül: `backend/routes/seftali/catalog.py` veya `products.py`

- ✅ `GET /api/seftali/sales/campaigns` (2 varyasyon) → **ambiguous / legacy**
  - Neden burada: kampanya okuma akışı iki farklı handler ile legacy biçimde kalmış
  - Şimdilik kalsın mı: **Evet**
  - İleride taşınmalı mı: **Evet**
  - Hedef modül: `backend/routes/seftali/campaigns.py`

- ✅ `POST /api/seftali/sales/campaigns/add-to-order` → **ambiguous**
  - Neden burada: order + campaign + working_copy arasında kesişim var
  - Şimdilik kalsın mı: **Evet**
  - İleride taşınmalı mı: **Evet**
  - Hedef modül: `backend/routes/seftali/campaigns.py` veya `order_actions.py`

- ✅ `GET /api/seftali/sales/plasiyer/route-customers/{route_day}` → **ambiguous**
  - Neden burada: müşteri listesi endpoint'i olsa da smart-order / rota akışıyla yakından ilişkili
  - Şimdilik kalsın mı: **Evet**
  - İleride taşınmalı mı: **Evet**
  - Hedef modül: `backend/routes/seftali/deliveries.py` veya `smart_orders.py` sonrası ayrı `routes.py`

#### Uygulanan Küçük Güvenli Cleanup
- ✅ `sales_routes.py` başına kısa internal note eklendi
- ✅ Dosyanın artık legacy / ambiguous leftovers tuttuğu açıklandı
- ✅ Endpoint path, response formatı ve iş mantığı değiştirilmedi

#### Sonraki Güvenli Batch Önerisi
- ✅ En güvenli sıradaki batch: `deliveries.py`
- Önerilen taşıma kapsamı:
  - `POST /api/seftali/sales/deliveries`
  - `GET /api/seftali/sales/deliveries`
- Neden güvenli: ownership net, smart-order/stock/customer/orders ile çakışması düşük

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ `pytest` ile doğrulandı: toplam `25/25` geçti

---

## ✅ SON GÜNCELLEME - SAFE BACKEND MIGRATION BATCH 5 (1 Nisan 2026)

### Yeni Özellikler

#### Order Route Ayrıştırması
- ✅ Yeni route modülü eklendi: `/app/backend/routes/seftali/orders.py`
- ✅ Mevcut servis genişletildi: `/app/backend/services/seftali/order_service.py`
- ✅ Sadece şu net order-scope endpointler `sales_routes.py` içinden taşındı:
  - `GET /api/seftali/sales/orders`
  - `POST /api/seftali/sales/orders/{order_id}/approve`
  - `POST /api/seftali/sales/orders/{order_id}/request-edit`
- ✅ Router register güncellendi: `routes/seftali/__init__.py`
- ✅ Aynı batch içinde taşınan order handler'ları `sales_routes.py` içinden kaldırıldı; duplicate route riski oluşmadı
- ✅ Endpoint path'leri, response formatı ve iş mantığı değiştirilmedi
- ✅ Belirsiz delivery/smart-order ownership taşıyan endpointler bu batch'te yerinde bırakıldı

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ `pytest` ile doğrulandı: toplam `25/25` geçti
- ✅ Canlı smoke doğrulaması yapıldı; `GET /orders`, `POST /orders/{id}/approve`, `POST /orders/{id}/request-edit` aynı response shape ile çalışıyor
- ✅ Yeni minimal contract test eklendi: `/app/backend/tests/test_plasiyer_orders_contracts.py`

---

## ✅ SON GÜNCELLEME - SAFE BACKEND MIGRATION BATCH 4 (1 Nisan 2026)

### Yeni Özellikler

#### Customer Route Ayrıştırması
- ✅ Yeni servis katmanı eklendi: `/app/backend/services/seftali/customer_service.py`
- ✅ Yeni route modülü eklendi: `/app/backend/routes/seftali/customers.py`
- ✅ Sadece şu net customer-scope endpointler `sales_routes.py` içinden taşındı:
  - `GET /api/seftali/sales/customers`
  - `GET /api/seftali/sales/customers/summary`
  - `GET /api/seftali/sales/customers/{customer_id}/consumption`
- ✅ Router register güncellendi: `routes/seftali/__init__.py`
- ✅ Aynı batch içinde taşınan customer handler'ları `sales_routes.py` içinden kaldırıldı; duplicate route riski oluşmadı
- ✅ Endpoint path'leri, response formatı ve iş mantığı değiştirilmedi
- ✅ Belirsiz ownership taşıyan endpointler (örn. müşteri güncelleme, ürün listesi, kampanya siparişe ekleme) bu batch'te yerinde bırakıldı

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ `pytest` ile doğrulandı: toplam `22/22` geçti
- ✅ Canlı smoke doğrulaması yapıldı; customer endpointleri aynı response shape ile çalışıyor
- ✅ Yeni minimal contract test eklendi: `/app/backend/tests/test_plasiyer_customer_contracts.py`

---

## ✅ SON GÜNCELLEME - SAFE BACKEND MIGRATION BATCH 3 (1 Nisan 2026)

### Yeni Özellikler

#### Plasiyer Stock Route Ayrıştırması
- ✅ Yeni servis katmanı eklendi: `/app/backend/services/seftali/stock_service.py`
- ✅ Yeni route modülü eklendi: `/app/backend/routes/seftali/stock.py`
- ✅ Sadece şu endpointler `sales_routes.py` içinden taşındı:
  - `GET /api/seftali/sales/plasiyer/stock`
  - `PATCH /api/seftali/sales/plasiyer/stock`
- ✅ Router register güncellendi: `routes/seftali/__init__.py`
- ✅ Aynı batch içinde taşınan stock handler'ları `sales_routes.py` içinden kaldırıldı; duplicate route riski oluşmadı
- ✅ Endpoint path'leri, response formatı ve iş mantığı değiştirilmedi

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ `pytest` ile doğrulandı: toplam `19/19` geçti
- ✅ Canlı smoke doğrulaması yapıldı; `GET/PATCH /api/seftali/sales/plasiyer/stock` eski response shape ile çalışıyor
- ✅ Yeni minimal contract test eklendi: `/app/backend/tests/test_plasiyer_stock_contracts.py`

---

## ✅ SON GÜNCELLEME - SAFE BACKEND MIGRATION BATCH 2.5 (1 Nisan 2026)

### Yeni Özellikler

#### Canonical Smart Orders Alias Adımı
- ✅ `smart_orders.py` içine yeni canonical alias endpoint'leri eklendi:
  - `GET /api/seftali/sales/smart-orders`
  - `POST /api/seftali/sales/smart-orders/submit`
- ✅ Legacy endpoint'ler korunuyor:
  - `GET /api/seftali/sales/warehouse-draft`
  - `POST /api/seftali/sales/warehouse-draft/submit`
- ✅ Her iki path grubu da aynı handler/service mantığını kullanıyor
- ✅ `SmartOrderService` içinde canonical method isimleri tanımlandı:
  - `get_smart_orders`
  - `submit_smart_orders`
- ✅ Eski method isimleri wrapper olarak bırakıldı:
  - `get_warehouse_draft`
  - `submit_warehouse_draft`

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ `pytest` ile doğrulandı: toplam `17/17` geçti
- ✅ Canlı GET doğrulaması yapıldı: `/warehouse-draft` ve `/smart-orders` birebir aynı response döndürüyor
- ✅ Her iki submit endpoint'i de aynı response shape ile çalışıyor

---

## ✅ SON GÜNCELLEME - SAFE BACKEND MIGRATION BATCH 2 (1 Nisan 2026)

### Yeni Özellikler

#### Smart Order Route Ayrıştırması
- ✅ Yeni route modülü eklendi: `/app/backend/routes/seftali/smart_orders.py`
- ✅ Aşağıdaki endpointler `sales_routes.py` içinden taşındı:
  - `GET /api/seftali/sales/warehouse-draft`
  - `POST /api/seftali/sales/warehouse-draft/submit`
  - `GET /api/seftali/sales/plasiyer/order-calculation`
  - `GET /api/seftali/sales/route-order/{route_day}`
  - `GET /api/seftali/sales/route-order`
- ✅ Router register güncellendi: `routes/seftali/__init__.py`
- ✅ Aynı batch içinde taşınan handler'lar `sales_routes.py` içinden kaldırıldı; duplicate route riski oluşmadı
- ✅ Endpoint path'leri, request/response formatı ve iş mantığı değiştirilmedi

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ `pytest` ile doğrulandı: smart-order contract testleri + warehouse draft testleri toplam `15/15` geçti
- ✅ Canlı endpoint smoke doğrulaması yapıldı; eski path'ler aynı response shape ile çalışıyor

---

## ✅ SON GÜNCELLEME - SAFE BACKEND MIGRATION BATCH 1 (1 Nisan 2026)

### Yeni Özellikler

#### Smart Order Güvenli Ayrıştırma Başlangıcı
- ✅ Smart Order endpoint contract testleri eklendi: `/app/backend/tests/test_smart_order_contracts.py`
- ✅ Yeni ince servis katmanı eklendi: `/app/backend/services/seftali/smart_order_service.py`
- ✅ `sales_routes.py` içindeki smart-order endpointleri bu servis katmanına yönlendirildi
- ✅ Bu batch'te endpoint path'leri ve response shape değiştirilmedi
- ✅ Çalışan davranış korunarak route -> service ayrımı başlatıldı

#### Doğrulama
- ✅ Python lint temiz geçti
- ✅ `pytest` ile doğrulandı: smart-order contract testleri + warehouse draft testleri toplam `15/15` geçti

---

## ✅ SON GÜNCELLEME - CUSTOMER ORDER SCREEN REDESIGN (1 Nisan 2026)

### Yeni Özellikler

#### Müşteri Sipariş Ekranı
- ✅ Mevcut `DraftView` ekranı yerinde yeniden tasarlandı
- ✅ Başlık `Sipariş Oluştur` ve sade müşteri odaklı alt açıklama eklendi
- ✅ Gerçek rota verisinden beslenen `Teslimat: <gün>` badge'i eklendi
- ✅ Ürün kartları plasiyer ekranıyla uyumlu ama daha sade hale getirildi
- ✅ `Önerilen` badge'i ve müşteri dostu açıklama metni eklendi
- ✅ Teknik/lojistik bilgiler kaldırıldı; yalnızca müşteri için anlaşılır bilgiler bırakıldı
- ✅ Quantity input stepper + manuel giriş olarak modernize edildi
- ✅ Öneri değeri input içine yazılmak yerine placeholder olarak gösteriliyor
- ✅ Alt kısma sticky sipariş özeti barı ve `Siparişi Gözden Geçir` CTA'sı eklendi
- ✅ Uyarı badge'leri sadeleştirildi: önerilen / dikkat / SKT

#### Doğrulama
- ✅ Testing agent ile backend + frontend testleri geçti (`/app/test_reports/iteration_8.json`)
- ✅ Ek olarak `CustomerDashboard` chart render warning'i için küçük render stabilizasyonu yapıldı
- ✅ Yeni regresyon testi eklendi: `/app/backend/tests/test_customer_draft_view.py`

---

## ✅ SON GÜNCELLEME - AILEM MARKET SMART ORDER TEST DATASET (1 Nisan 2026)

### Yeni Özellikler

#### Test Verisi Yükleme
- ✅ Ailem Market için akıllı sipariş test senaryosu sisteme yüklendi
- ✅ Müşteri rota günleri tekrar `MON` / `FRI` olarak ayarlandı
- ✅ Sadece 2 test ürünüyle temiz veri seti oluşturuldu:
  - `Ayran 2L`
  - `Kova Yoğurt`
- ✅ 4 kabul edilmiş teslimat/fatura senaryosu yüklendi:
  - Mon: Ayran 400, Yoğurt 10
  - Fri: Ayran 300
  - Mon: Ayran 400, Yoğurt 10
  - Fri: Ayran 300
- ✅ `de_customer_product_state` yeniden oluşturuldu
- ✅ `sf_daily_consumption` kayıtları dolduruldu
- ✅ Beklenen çıktı dokümanı oluşturuldu: `/app/test_reports/ailem_market_smart_order_expected.json`

#### Doğrulama
- ✅ Müşteri draft endpoint'i artık yalnızca bu 2 ürün için veri dönüyor
- ✅ Günlük tüketim özeti doğrulandı:
  - Ayran 2L = `100.0 / gün`
  - Kova Yoğurt = `1.4286 / gün`
- ✅ Working copy başlatma akışı test için hazır
- ⚠️ Not: Canlı `/api/seftali/customer/draft` çıktısı mevcut backend tarih mantığına göre **bugünden sonraki aktif rota penceresi** için hesaplanır; bu yüzden tarihsel senaryo beklenen çıktısı ayrıca JSON dosyasında saklandı

---

## ✅ SON GÜNCELLEME - AKILLI SİPARİŞ UI REDESIGN (24 Mart 2026)

### Yeni Özellikler

#### Depo Sipariş Oluştur Ekranı
- ✅ Mevcut `WarehouseDraftPage` ekranı yeniden tasarlandı
- ✅ Başlık + rota günü alt başlığı + sağda `Bakiye` badge eklendi
- ✅ `Rut Müşterisi / Sipariş Veren / Taslakta` için gradient özet kartları eklendi
- ✅ Ürün listesi tablo hissinden çıkarılıp ayrı soft kartlara dönüştürüldü
- ✅ Ürün kartlarında depo stoğu, SKT, plasiyer stoğu, toplam adet + koli vurgusu ve tahmini ihtiyaç alanı netleştirildi
- ✅ `plasiyer_stock = 0` için kırmızı, `> 0` için yeşil görsel mantık uygulandı
- ✅ `Tahmini ihtiyaç` dropdown’ı mevcut mantık korunarak modernleştirildi
- ✅ Kesim saati uyarısı amber alert kutusuna dönüştürüldü
- ✅ Backend mantığı korunarak sadece frontend redesign yapıldı

#### Test ve Doğrulama
- ✅ Smoke test alındı
- ✅ Testing agent ile backend + frontend testleri geçti (`/app/test_reports/iteration_7.json`)
- ✅ Yeni regresyon testi eklendi: `/app/backend/tests/test_warehouse_draft.py`

---

## ✅ SON GÜNCELLEME - RUT SAYFASI YENİDEN TASARIMI (21 Mart 2026)

### Yeni Özellikler

#### Plasiyer Rut Dashboard Güncellemesi
- ✅ `RutPage` referans görsele göre yeniden tasarlandı
- ✅ Sol sidebar + üst header korunarak sadece Rut ekranı modernize edildi
- ✅ Sayfa başlığı `Bugünün Noktaları` formatına geçirildi
- ✅ Tarih + toplam nokta özeti eklendi
- ✅ Turuncu / yeşil bölünmüş rota özet barı eklendi
- ✅ Özet bar oransal hale getirildi; pending/visited segment genişlikleri toplam nokta sayısına göre dinamik hesaplanıyor
- ✅ `Bekleyen Noktalar` ve `Gidilmiş Noktalar` bölümleri ayrı beyaz kartlar olarak kurgulandı
- ✅ Satır tıklamasında açılan read-only rota detay drawer'ı eklendi
- ✅ Bekleyen noktalar için yeniden kullanılabilir `RouteActionModal` eklendi
- ✅ Modal içinde Konum / Mesajlar / Fatura Oluştur aksiyonları, tek seçimli ziyaret sonucu ve `Seç` onayı eklendi
- ✅ Modal onayı sonrası öğe pending/visited listeleri arasında lokal state ile taşınıyor
- ✅ Görselleştirme için mevcut müşteriler üzerinde kalıcı test verisi ayarlandı: bugün için 8 nokta, 5 visited + 3 pending, sıra 1–8
- ✅ Boş gün senaryosunda bile iki bölüm yapısı korunuyor

#### Rut Veri Eşleme Mantığı
- ✅ Rut ekranı artık `GET /api/seftali/sales/plasiyer/route-customers/{route_day}` endpoint'inden besleniyor
- ✅ Sıralama için frontend normalizasyonu eklendi:
  - `visit_order`
  - `route_plan.sequence`
  - `route_order`
  - fallback: mevcut liste sırası
- ✅ Dinamik yeniden sıralama yok; tanımlı rota sırası korunuyor
- ✅ Görsel durum ayrımı için pending / visited listeleri oluşturuldu

#### Test ve Doğrulama
- ✅ Smoke test alındı
- ✅ Testing agent ile backend + frontend testleri geçti (`/app/test_reports/iteration_5.json`)
- ✅ RouteActionModal akışı ayrıca doğrulandı (`/app/test_reports/iteration_6.json`)
- ✅ Yeni regresyon testi eklendi: `/app/backend/tests/test_rut_page.py`

---

## ✅ SON GÜNCELLEME - BÖLGE YÖNETİMİ (5 Mart 2026)

### Yeni Özellikler

#### Bölge Yönetimi Sistemi
- ✅ `sf_regions` koleksiyonu oluşturuldu
- ✅ Bölgeler depolara bağlanabiliyor (örn: İstanbul Merkez → D001)
- ✅ Plasiyerlere bölge atanabiliyor (`region_id` alanı eklendi)
- ✅ Müşterilere bölge atanabiliyor (`region_id` alanı eklendi)
- ✅ Admin Dashboard'a "Bölgeler" sekmesi eklendi

#### Plasiyer Akıllı Sipariş Güncellemesi
- ✅ **Depo Stoğu**: Plasiyerin bağlı olduğu bölgenin deposundaki stok gösteriliyor
- ✅ **SKT**: Depo stoğundaki ürünün son kullanma tarihi gösteriliyor
- ✅ **Plasiyer Stoğu**: Plasiyerin kendi stoğu gösteriliyor
- ✅ **Koli Hesaplama**: Net ihtiyaç = Toplam - Plasiyer Stoğu, sonra koliye yuvarla
  - Örnek: Toplam 28, Plasiyer stoğu 10 → İhtiyaç 18 → 20'lik koliye yuvarla = 20 adet (1 koli)

#### Yeni API Endpoint'leri
- `GET /api/seftali/admin/regions` - Bölge listesi
- `POST /api/seftali/admin/regions` - Yeni bölge oluştur
- `PATCH /api/seftali/admin/regions/{id}` - Bölge güncelle
- `DELETE /api/seftali/admin/regions/{id}` - Bölge sil
- `POST /api/seftali/admin/regions/seed` - İstanbul Merkez bölgesini oluştur
- `PATCH /api/seftali/admin/customers/{id}/region` - Müşteri bölgesi ata
- `PATCH /api/seftali/admin/users/{id}/region` - Plasiyer bölgesi ata
- `GET /api/seftali/admin/users/plasiyerler` - Plasiyer listesi
- `GET /api/seftali/admin/customers` - Müşteri listesi (admin)
- `GET /api/seftali/sales/warehouse-draft` - Güncellendi: Depo stoğu, SKT, plasiyer stoğu içeriyor

#### Admin Bölge Yönetimi UI
- Bölgeler sekmesi: Bölge listesi, ekleme, düzenleme, silme
- Plasiyerler alt sekmesi: Bölge atama dropdown
- Müşteriler alt sekmesi: Bölge atama dropdown
- İstatistik kartları: Toplam bölge, aktif bölge, plasiyer sayısı, bölgesi olmayan müşteri

---

## Önceki Güncellemeler

### Refactoring (26 Şubat 2026)

#### Backend OOP Refactoring
- ✅ Tüm iş mantığı `/app/backend/services/seftali/` altında service sınıflarına taşındı
- ✅ `core.py`: Ortak sabitler, yardımcı fonksiyonlar
- ✅ `draft_engine.py`: Draft Engine 2.0 hesaplamaları
- ✅ `order_service.py`: Plasiyer sipariş hesaplama servisi
- ✅ Route dosyaları basitleştirildi (controller görevi)

#### Route Order Endpoint Düzeltmesi
- ✅ `GET /api/seftali/sales/route-order/{route_day}` endpoint'i eklendi
- ✅ Koli yuvarlama çalışıyor

#### Frontend Component Düzeltmeleri
- ✅ Eksik placeholder component'ler oluşturuldu:
  - CustomerManagement.js
  - AllCustomersConsumption.js  
  - BulkImport.js
  - CustomerForm.js
  - InventoryView.js
  - IncomingShipments.js

### Plasiyer Panel - Sidebar Menu Refactoring (Aralık 2025)
- **"Depo Taslağı" tab renamed to "Akıllı Sipariş"**
- **Old empty "Akıllı Sipariş" (draft-engine) tab removed**
- **New "Akıllı Sipariş" page redesigned** according to user's visual requirements

---

## Çalışan Dashboard'lar
- ✅ **Plasiyer Dashboard**: Ana sayfa, Müşteriler, Rota Siparişi, Teslimatlar
- ✅ **Customer Dashboard**: Ana sayfa, Sipariş, Teslimat Onayı, Analizler
- ✅ **Admin Dashboard**: Genel Bakış, Bölgeler, Kampanyalar, Müşteriler, Ürünler, Teslimatlar

---

## Tech Stack
- **Backend:** FastAPI (Python), MongoDB
- **Frontend:** React, Tailwind CSS, Shadcn/UI

## Demo Kullanıcılar
- Müşteri: `sf_musteri` / `musteri123`
- Plasiyer: `sf_plasiyer` / `plasiyer123`
- Admin: `admin` / `admin123`

---

## P0 - Tamamlandı ✅
- [x] Draft Engine 2.0 entegrasyonu
- [x] Plasiyer Rota Siparişi hesaplama
- [x] OOP Refactoring
- [x] Frontend stabilizasyonu
- [x] Stok Yönetimi (Admin ürün sayfası)
- [x] **Bölge Yönetimi Sistemi**
  - Bölge CRUD işlemleri
  - Müşteri-Bölge ataması
  - Plasiyer-Bölge ataması
  - İstanbul Merkez → D001 (İstanbul Merkez Depo) bağlantısı

## P1 - Yaklaşan Görevler
- [ ] Rut detay ekranı içeriğini kullanıcının vereceği yeni detaylara göre genişlet
- [ ] Cutoff Time Trigger'ı supervisor ile yapılandır
- [ ] Admin Ayarları UI sayfası oluştur
- [ ] Haftalık çarpan batch job'ını aktive et

## P2 - Gelecek Görevler
- [ ] "Sipariş Gönder" butonu (Rota Siparişi)
- [ ] Yeni ürün ekleme (Admin)
- [ ] Plasiyer stok defteri/raporlama
- [ ] Admin raporları ve analizler sayfaları
- [ ] Bildirim sistemi

## P3 - Backlog
- [ ] Real SMS/WhatsApp entegrasyonu
- [ ] Mobile responsive iyileştirmeler
- [ ] Multi-tenant desteği
