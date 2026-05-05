import sys
from decimal import Decimal
from datetime import date

import pytest

sys.path.insert(0, '/app/backend')
from services.efatura.contracts import EInvoiceCreateRequest
from services.efatura.provider_adapter import ProviderError, TurkcellEFaturaProviderAdapter
from services.efatura.invoice_service import EInvoiceService
from services.efatura.ubl_builder import UBLInvoiceBuilder


def test_internal_payload_to_ubl_generation():
    builder = UBLInvoiceBuilder('1234567803', 'TEST GÖNDERİCİ')
    payload = EInvoiceCreateRequest(
        local_reference_id='INV-2026-0001',
        issue_date=date(2026, 4, 20),
        receiver={
            'vkn_tckn': '1234567803',
            'alias': 'urn:mail:defaulttest3pk@medyasoft.com.tr',
            'title': 'TEST ALICI',
        },
        lines=[{
            'name': '2000 ml Ayran',
            'quantity': Decimal('10'),
            'unit_code': 'NIU',
            'unit_price': Decimal('45.00'),
            'vat_rate': Decimal('10'),
        }],
    )
    xml = builder.build(payload)
    assert '<cbc:ID>INV-2026-0001</cbc:ID>' in xml
    assert 'TEST ALICI' in xml
    assert '1234567803' in xml
    assert '2000 ml Ayran' in xml


@pytest.mark.asyncio
async def test_create_invoice_service_unit(monkeypatch):
    class FakeRepo:
        async def ensure_indexes(self):
            return None
        async def find_by_local_reference_id(self, local_reference_id):
            return None
        async def create_invoice(self, payload):
            self.payload = payload
            return payload
        async def update_invoice(self, invoice_id, updates):
            self.updates = updates
            return {**self.payload, **updates, 'id': invoice_id}
        async def get_invoice(self, invoice_id):
            return {**self.payload, **self.updates, 'id': invoice_id}
        async def insert_provider_log(self, payload):
            self.log = payload

    class FakeProvider:
        async def createInvoiceFromUbl(self, xml, metadata):
            return {
                'http_status': 202,
                'payload': {'providerInvoiceId': 'prov-1', 'statusCode': '202', 'statusMessage': 'accepted'},
                'provider_invoice_id': 'prov-1',
                'provider_status_code': '202',
                'provider_status_message': 'accepted',
                'normalized_status': 'queued',
            }
        def next_poll_delay_seconds(self, attempt_count):
            return 10

    service = EInvoiceService(repository=FakeRepo(), provider=FakeProvider(), ubl_builder=UBLInvoiceBuilder('1234567803', 'TEST GÖNDERİCİ'))
    payload = EInvoiceCreateRequest(
        local_reference_id='INV-2026-0002',
        issue_date=date(2026, 4, 20),
        receiver={'vkn_tckn': '1234567803', 'alias': 'urn:mail:defaulttest3pk@medyasoft.com.tr', 'title': 'TEST ALICI'},
        lines=[{'name': 'Ayran', 'quantity': Decimal('1'), 'unit_code': 'NIU', 'unit_price': Decimal('10'), 'vat_rate': Decimal('10')}],
    )
    result = await service.create_and_send(payload)
    assert result.status.value == 'queued'
    assert result.provider_invoice_id == 'prov-1'


def test_provider_response_normalization(monkeypatch):
    monkeypatch.setenv('TURKCELL_EINVOICE_BASE_URL', 'https://example.test')
    monkeypatch.setenv('TURKCELL_EINVOICE_CREATE_PATH', '/create')
    monkeypatch.setenv('TURKCELL_EINVOICE_STATUS_PATH', '/status/{id}')
    monkeypatch.setenv('TURKCELL_EINVOICE_API_KEY', 'test-key')
    adapter = TurkcellEFaturaProviderAdapter()
    assert adapter.normalize_create_status(202, {'statusMessage': 'processing'}) == 'queued'
    assert adapter.normalize_status_payload({'statusMessage': 'accepted'}) == 'sent'
    assert adapter.normalize_status_payload({'statusMessage': 'rejected'}) == 'failed'

@pytest.mark.asyncio
async def test_provider_create_uses_multipart_form(monkeypatch):
    monkeypatch.setenv('TURKCELL_EINVOICE_BASE_URL', 'https://example.test')
    monkeypatch.setenv('TURKCELL_EINVOICE_CREATE_PATH', '/v2/outboxinvoice')
    monkeypatch.setenv('TURKCELL_EINVOICE_STATUS_PATH', '/v2/outboxinvoice/{id}/status')
    monkeypatch.setenv('TURKCELL_EINVOICE_API_KEY', 'test-key')
    adapter = TurkcellEFaturaProviderAdapter()
    captured = {}

    async def fake_request(method, url, **kwargs):
        captured['method'] = method
        captured['url'] = url
        captured['kwargs'] = kwargs
        class Resp:
            status_code = 200
            headers = {'content-type': 'application/json'}
            def json(self):
                return {'Id': 'prov-1', 'InvoiceNumber': 'EFA-1', 'statusMessage': 'processing'}
        return Resp()

    monkeypatch.setattr(adapter, '_request', fake_request)
    result = await adapter.createInvoiceFromUbl('<xml/>', {'local_reference_id': 'INV-1'})
    assert captured['method'] == 'POST'
    assert captured['url'].endswith('/v2/outboxinvoice')
    assert 'files' in captured['kwargs']
    assert 'invoiceFile' in captured['kwargs']['files']
    assert captured['kwargs']['data']['appType'] == '1'
    assert captured['kwargs']['data']['status'] == '20'
    assert captured['kwargs']['data']['localReferenceId'] == 'INV-1'
    assert captured['kwargs']['data']['checkLocalReferenceId'] == 'true'
    assert captured['kwargs']['data']['useFirstAlias'] == 'true'
    assert result['provider_invoice_id'] == 'prov-1'
    assert result['invoice_number'] == 'EFA-1'


@pytest.mark.asyncio
async def test_provider_status_uses_path_id(monkeypatch):
    monkeypatch.setenv('TURKCELL_EINVOICE_BASE_URL', 'https://example.test')
    monkeypatch.setenv('TURKCELL_EINVOICE_CREATE_PATH', '/v2/outboxinvoice')
    monkeypatch.setenv('TURKCELL_EINVOICE_STATUS_PATH', '/v2/outboxinvoice/{id}/status')
    monkeypatch.setenv('TURKCELL_EINVOICE_API_KEY', 'test-key')
    adapter = TurkcellEFaturaProviderAdapter()
    captured = {}

    async def fake_request(method, url, **kwargs):
        captured['method'] = method
        captured['url'] = url
        captured['kwargs'] = kwargs
        class Resp:
            status_code = 200
            headers = {'content-type': 'application/json'}
            def json(self):
                return {'Id': 'prov-2', 'envelopeStatus': 'processing'}
        return Resp()

    monkeypatch.setattr(adapter, '_request', fake_request)
    result = await adapter.getInvoiceStatus('prov-2')
    assert captured['url'].endswith('/v2/outboxinvoice/prov-2/status')
    assert 'params' not in captured['kwargs']
    assert result['provider_invoice_id'] == 'prov-2'
    assert result['normalized_status'] == 'processing'

    assert adapter._extract_provider_invoice_id({'Id': '123'}) == '123'
    assert adapter._extract_invoice_number({'InvoiceNumber': 'ABC-1'}) == 'ABC-1'


@pytest.mark.asyncio
async def test_status_update(monkeypatch):
    class FakeRepo:
        async def get_invoice(self, invoice_id):
            return {'id': invoice_id, 'provider_invoice_id': 'prov-1', 'status_check_attempts': 0, 'status': 'queued'}
        async def update_invoice(self, invoice_id, updates):
            return {'id': invoice_id, **updates}
        async def insert_provider_log(self, payload):
            self.log = payload

    class FakeProvider:
        async def getInvoiceStatus(self, provider_invoice_id):
            return {
                'http_status': 200,
                'payload': {'statusMessage': 'accepted'},
                'provider_status_code': '200',
                'provider_status_message': 'accepted',
                'normalized_status': 'sent',
            }
        def next_poll_delay_seconds(self, attempt_count):
            return 10

    service = EInvoiceService(repository=FakeRepo(), provider=FakeProvider(), ubl_builder=None)
    result = await service.refresh_status('inv-1')
    assert result.status.value == 'sent'


@pytest.mark.asyncio
async def test_test_smoke_endpoint(monkeypatch):
    from routes.invoices_routes import create_test_smoke_invoice

    class FakeUser:
        role = 'admin'

    class FakeResult:
        def model_dump(self):
            return {'invoice_id': 'inv-1', 'status': 'queued'}

    async def fake_smoke(self):
        return FakeResult()

    def fake_init(self, repository=None, provider=None, ubl_builder=None):
        self.repository = repository
        self.provider = provider
        self.ubl_builder = ubl_builder

    monkeypatch.setattr(EInvoiceService, '__init__', fake_init)
    monkeypatch.setattr(EInvoiceService, 'create_test_smoke_invoice', fake_smoke)
    response = await create_test_smoke_invoice(current_user=FakeUser())
    assert response['success'] is True
    assert response['data']['invoice_id'] == 'inv-1'
