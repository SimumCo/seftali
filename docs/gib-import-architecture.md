# GİB Import / Draft Customer Mimari Notu

## Referans Repo Analizi

Referans repo: `https://github.com/ciwga/gib-otomasyon`

Yeniden kullanılabilecek parçalar:
- `gib_otomasyon/scraper/browser.py`
  - portal oturumu / browser akışı mantığı
- `gib_otomasyon/scraper/engine.py`
  - fatura listeleme, sayfalama, indirme akışı
- `gib_otomasyon/parser/html_parser.py`
  - HTML faturadan alan çıkarma yaklaşımı
- `gib_otomasyon/models.py`
  - invoice / line item veri modelleme yaklaşımı
- `config.yaml` + `config.py`
  - seçici/config ayrıştırma fikri

Bu repodan alınmayacak parçalar:
- CLI arayüzü
- GUI arayüzü
- raporlama katmanı
- converter / PDF odaklı parçalar
- standalone kullanım akışı

Bu projede referans repo şu amaçla kullanılacak:
- GİB portalından geçmiş fatura çekme mantığı
- HTML parse edip `invoice` + `invoice_lines` üretme
- tc_no / vergi_no bazlı müşteri adaylarını çıkarma

## Yeni İzole Backend Modül Yapısı

```text
backend/services/gib_import/
├── __init__.py
├── constants.py
├── contracts.py
├── import_service.py
├── draft_customer_service.py
├── customer_approval_service.py
├── invoice_link_service.py
└── consumption_service.py
```

## Sorumluluklar

### import_service.py
- GİB import job başlatma
- canlı portal entegrasyonuna hazır koordinasyon katmanı
- idempotent invoice ingestion başlangıç noktası

### draft_customer_service.py
- faturaları tc_no / vergi_no bazında gruplayıp `draft_customers` üretme
- duplicate draft üretmeme
- invoice_count / first_invoice_date / last_invoice_date / total_amount hesaplama

### customer_approval_service.py
- draft customer → approved customer dönüşümü
- `customer_users` oluşturma
- `must_change_password = true`

### invoice_link_service.py
- onaylanan customer ile geçmiş faturaları bağlama
- idempotent `customer_id` set etme

### consumption_service.py
- aynı müşteri + aynı ürün bazında fatura aralıklarından günlük tüketim hesaplama
- `customer_product_consumptions` upsert etme

## Collection Tasarım Prensibi

Bu batch'te yeni yapı **izole** kurulmuştur.

Önemli not:
- mevcut çalışan ŞEFTALİ koleksiyonları doğrudan bozulmuyor
- yeni akış için gereken collection/index bootstrap script ile kuruluyor
- mevcut `products` ve `invoices` koleksiyonlarında additive / güvenli index yaklaşımı kullanılıyor

## Bu Batch'te Yapılanlar
- modül iskeleti oluşturuldu
- collection/index bootstrap script yazıldı
- canlı GİB login/test bilinçli olarak ertelendi
- sonraki batch için import-ready temel atıldı

## Sonraki Güvenli Batch
- import service içine gerçek parser adapter'ı ekleme
- `POST /gib/import/start`
- `GET /draft-customers`
- idempotent invoice + invoice_lines yazımı
