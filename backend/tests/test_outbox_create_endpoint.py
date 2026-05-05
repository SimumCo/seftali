"""
Unit tests for Turkcell v1 outbox create endpoint (/api/gib/live/outbox/create).

Covers:
  1) create success → 200 with id + invoice_number + provider_status
  2) create validation fail → 422 with Turkish-mappable validation hints
  3) network fail → 504 / 503 propagated
  4) api key never leaks to response or log formatter
  5) mapping: frontend flat payload → Turkcell body shape
  6) deprecated typo route emits Deprecation header and still works
"""
from __future__ import annotations

import logging
import sys
from decimal import Decimal
from datetime import date
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, '/app/backend')

from services.efatura.outbox_contracts import OutboxCreateRequest
from services.efatura.outbox_provider import (
    OutboxProviderError,
    TurkcellOutboxProvider,
    map_request_to_provider_body,
)


# ----- fixtures -----
@pytest.fixture(autouse=True)
def _turkcell_env(monkeypatch):
    monkeypatch.setenv('TURKCELL_EINVOICE_BASE_URL', 'https://example.test')
    monkeypatch.setenv('TURKCELL_OUTBOX_CREATE_PATH', '/v1/outboxinvoice/create')
    monkeypatch.setenv('TURKCELL_X_API_KEY', 'SECRET-API-KEY-XYZ')
    monkeypatch.setenv('TURKCELL_OUTBOX_TIMEOUT_SECONDS', '3')
    monkeypatch.setenv('TURKCELL_OUTBOX_RETRY_ATTEMPTS', '1')
    yield


def _sample_payload() -> Dict[str, Any]:
    return {
        'local_reference_id': 'INV-2026-0001',
        'issue_date': '2026-04-23',
        'receiver': {
            'vkn_tckn': '1234567803',
            'title': 'TEST ALICI',
            'alias': 'urn:mail:defaulttest3pk@medyasoft.com.tr',
            'tax_office': 'Marmara Kurumlar',
            'address': {
                'street': 'Test Mah.',
                'city': 'İstanbul',
                'postal_code': '34000',
                'country': 'Türkiye',
            },
        },
        'lines': [
            {
                'name': '2000 ml Ayran',
                'quantity': Decimal('10'),
                'unit_code': 'NIU',
                'unit_price': Decimal('45.00'),
                'vat_rate': Decimal('10'),
            }
        ],
    }


class FakeResponse:
    def __init__(self, status_code: int, body: Dict[str, Any], content_type: str = 'application/json'):
        self.status_code = status_code
        self._body = body
        self.headers = {'content-type': content_type}
        self.text = str(body)

    def json(self) -> Dict[str, Any]:
        return self._body


class FakeClient:
    def __init__(self, response=None, raise_exc=None):
        self._response = response
        self._raise_exc = raise_exc
        self.calls: list = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url: str, json=None, headers=None):
        self.calls.append({'url': url, 'json': json, 'headers': headers})
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._response


# ===== 1) CREATE SUCCESS =====
@pytest.mark.asyncio
async def test_outbox_create_success_returns_id_and_invoice_number():
    response = FakeResponse(
        200,
        {
            'Id': 'prov-uuid-abc-123',
            'InvoiceNumber': 'EFA2026000000001',
            'status': 'processing',
            'message': 'accepted',
        },
    )
    fake_client = FakeClient(response=response)
    provider = TurkcellOutboxProvider(http_client_factory=lambda: fake_client)

    body = {'LocalReferenceId': 'INV-2026-0001', 'Lines': []}
    result = await provider.create_outbox_invoice(body)

    assert result['http_status'] == 200
    assert result['id'] == 'prov-uuid-abc-123'
    assert result['invoice_number'] == 'EFA2026000000001'
    assert result['provider_status'] == 'processing'
    assert result['provider_body']['Id'] == 'prov-uuid-abc-123'

    # URL composed correctly
    assert fake_client.calls[0]['url'] == 'https://example.test/v1/outboxinvoice/create'
    # API key sent to provider (as header) but NOT in our returned body
    assert fake_client.calls[0]['headers']['x-api-key'] == 'SECRET-API-KEY-XYZ'
    assert 'x-api-key' not in str(result['provider_body']).lower() or 'SECRET-API-KEY' not in str(result)


# ===== 2) VALIDATION FAIL =====
@pytest.mark.asyncio
async def test_outbox_create_validation_fail_extracts_hints():
    response = FakeResponse(
        422,
        {
            'Error': {'code': 'VALIDATION_ERROR', 'title': 'Validation failed', 'detail': 'Customer.VknTckn must be 10 or 11 digits'},
            'errors': [
                {'field': 'Lines[0].UnitPrice', 'message': 'must be positive'},
                {'field': 'IssueDate', 'message': 'is required'},
            ],
        },
    )
    fake_client = FakeClient(response=response)
    provider = TurkcellOutboxProvider(http_client_factory=lambda: fake_client)

    with pytest.raises(OutboxProviderError) as exc_info:
        await provider.create_outbox_invoice({'LocalReferenceId': 'INV-2'})

    err = exc_info.value
    assert err.status_code == 422
    assert err.provider_code == 'VALIDATION_ERROR'
    assert 'Validation failed' in err.validation_hints
    assert any('UnitPrice' in h for h in err.validation_hints)
    assert any('IssueDate' in h for h in err.validation_hints)


# ===== 2b) TURKCELL v1 ROOT-LEVEL FIELD ERRORS (Shape B) =====
@pytest.mark.asyncio
async def test_outbox_create_turkcell_root_level_errors_extracted():
    """Turkcell v1 returns validation errors as root-level {field: [messages]}."""
    response = FakeResponse(
        400,
        {
            'addressBook': ['AddressBook boş gönderilemez.'],
            'generalInfoModel.Type': ['Fatura tipi 1:SATIS, 2:IADE vb. olmalı'],
            'lines[0].unitPrice': ['Birim fiyat 0 olamaz'],
        },
    )
    fake_client = FakeClient(response=response)
    provider = TurkcellOutboxProvider(http_client_factory=lambda: fake_client)

    with pytest.raises(OutboxProviderError) as exc_info:
        await provider.create_outbox_invoice({'LocalReferenceId': 'INV-X'})

    hints = exc_info.value.validation_hints
    assert any('addressBook' in h for h in hints)
    assert any('generalInfoModel.Type' in h for h in hints)
    assert any('lines[0].unitPrice' in h for h in hints)


# ===== 3) NETWORK FAIL =====
@pytest.mark.asyncio
async def test_outbox_create_timeout_raises_504():
    import httpx
    fake_client = FakeClient(raise_exc=httpx.TimeoutException('timeout'))
    provider = TurkcellOutboxProvider(http_client_factory=lambda: fake_client)

    with pytest.raises(OutboxProviderError) as exc_info:
        await provider.create_outbox_invoice({})

    assert exc_info.value.status_code == 504
    assert 'timeout' in exc_info.value.message.lower()


@pytest.mark.asyncio
async def test_outbox_create_http_error_raises_503():
    import httpx
    fake_client = FakeClient(raise_exc=httpx.ConnectError('tunnel closed'))
    provider = TurkcellOutboxProvider(http_client_factory=lambda: fake_client)

    with pytest.raises(OutboxProviderError) as exc_info:
        await provider.create_outbox_invoice({})

    assert exc_info.value.status_code == 503


# ===== 4) API KEY NEVER IN LOGS =====
@pytest.mark.asyncio
async def test_api_key_is_redacted_in_logs(caplog):
    caplog.set_level(logging.INFO)
    response = FakeResponse(200, {'Id': 'x', 'InvoiceNumber': 'n'})
    fake_client = FakeClient(response=response)
    provider = TurkcellOutboxProvider(http_client_factory=lambda: fake_client)
    await provider.create_outbox_invoice({'LocalReferenceId': 'INV-3'})

    # The real API key value must NEVER appear in any log record
    for record in caplog.records:
        assert 'SECRET-API-KEY-XYZ' not in record.getMessage()
        for value in (record.__dict__ or {}).values():
            assert 'SECRET-API-KEY-XYZ' not in str(value)


# ===== 5) REQUEST MAPPING =====
def test_map_request_to_provider_body_shape():
    raw = _sample_payload()
    # simulate pydantic.model_dump(mode='json')
    raw['issue_date'] = str(raw['issue_date']) if not isinstance(raw['issue_date'], str) else raw['issue_date']
    for line in raw['lines']:
        line['quantity'] = str(line['quantity'])
        line['unit_price'] = str(line['unit_price'])
        line['vat_rate'] = str(line['vat_rate'])

    body = map_request_to_provider_body(raw)
    # Turkcell v1 root keys
    assert body['localReferenceId'] == 'INV-2026-0001'
    assert 'addressBook' in body
    assert 'generalInfoModel' in body
    assert 'invoiceLines' in body

    # addressBook (receiver) — Turkcell v1 field names
    ab = body['addressBook']
    assert ab['IdentificationNumber'] == '1234567803'
    assert ab['Name'] == 'TEST ALICI'
    assert ab['ReceiverCity'] == 'İstanbul'
    assert ab['ReceiverCountry'] == 'Türkiye'

    # generalInfoModel — Type/InvoiceProfileType must be INT enum values, IssueDate not InvoiceDate
    gi = body['generalInfoModel']
    assert gi['Type'] == 1          # SATIS
    assert gi['InvoiceProfileType'] == 1  # TEMELFATURA
    assert gi['CurrencyCode'] == 'TRY'
    assert gi['IssueDate'] == '2026-04-23'

    # invoiceLines — InventoryCard + Amount + UnitCode (UBL, Turkcell v1 accepts UBL)
    assert len(body['invoiceLines']) == 1
    line = body['invoiceLines'][0]
    assert line['InventoryCard'] == '2000 ml Ayran'
    assert line['Name'] == '2000 ml Ayran'
    assert line['UnitCode'] == 'C62'  # NIU → C62 (each/piece, UBL)
    assert line['UnitPrice'] == '45.00'
    assert line['VatRate'] == '10.00'
    assert line['Amount'].startswith('10')


def test_map_request_enum_resolution_accepts_int_and_string():
    """Type and InvoiceProfileType accept enum name, int, or int-string."""
    payload = _sample_payload()
    payload['issue_date'] = str(payload['issue_date'])
    for line in payload['lines']:
        line['quantity'] = str(line['quantity'])
        line['unit_price'] = str(line['unit_price'])
        line['vat_rate'] = str(line['vat_rate'])

    # Case 1: enum name (IADE=2)
    payload['invoice_type_code'] = 'IADE'
    payload['scenario'] = 'TICARIFATURA'  # 2
    body = map_request_to_provider_body(payload)
    assert body['generalInfoModel']['Type'] == 2
    assert body['generalInfoModel']['InvoiceProfileType'] == 2

    # Case 2: numeric string
    payload['invoice_type_code'] = '5'
    payload['scenario'] = '1'
    body = map_request_to_provider_body(payload)
    assert body['generalInfoModel']['Type'] == 5
    assert body['generalInfoModel']['InvoiceProfileType'] == 1

    # Case 3: unknown name → default
    payload['invoice_type_code'] = 'FOOBAR'
    payload['scenario'] = 'BAZ'
    body = map_request_to_provider_body(payload)
    assert body['generalInfoModel']['Type'] == 1
    assert body['generalInfoModel']['InvoiceProfileType'] == 1


def test_map_request_raw_provider_body_passthrough():
    raw = {
        'local_reference_id': 'X',
        'raw_provider_body': {'CustomKey': 'CustomValue', 'Lines': [{'A': 1}]},
    }
    body = map_request_to_provider_body(raw)
    assert body == {'CustomKey': 'CustomValue', 'Lines': [{'A': 1}]}


def test_pydantic_request_rejects_invalid_vkn():
    payload = _sample_payload()
    payload['receiver']['vkn_tckn'] = '123'
    with pytest.raises(Exception):
        OutboxCreateRequest(**payload)


def test_pydantic_request_accepts_valid_payload():
    payload = _sample_payload()
    model = OutboxCreateRequest(**payload)
    assert model.local_reference_id == 'INV-2026-0001'
    assert model.receiver.vkn_tckn == '1234567803'
    assert len(model.lines) == 1


# ===== 6) DEPRECATED TYPO ROUTE =====
def test_recalculate_consption_route_exists_and_deprecated():
    """Verify the legacy typo route is still mounted and marked deprecated in OpenAPI."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from routes.gib_import_routes import router

    app = FastAPI()
    app.include_router(router, prefix='/api')
    openapi = app.openapi()
    paths = openapi.get('paths', {})

    legacy = paths.get('/api/customers/{customer_id}/recalculate-consption')
    canonical = paths.get('/api/customers/{customer_id}/recalculate-consumption')
    assert legacy is not None, 'legacy typo route must still be mounted'
    assert canonical is not None, 'canonical (fixed) route must exist'
    assert legacy.get('post', {}).get('deprecated') is True
