"""Mock-only tests for e-Belge integration.

Bu testler ASLA gerçek Turkcell provider'a istek atmaz — tüm HTTP çağrıları
monkeypatch ile kapatılır. Provider contract'a göre örnek response bodyler
kullanılır.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure backend root on path when running via pytest from repo root
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest  # noqa: E402

os.environ.setdefault("TURKCELL_EBELGE_API_KEY", "test-key-123")
os.environ.setdefault("TURKCELL_EBELGE_ENV", "test")

from services.ebelge import (  # noqa: E402
    DocumentKind,
    TurkcellEBelgeClient,
    TurkcellEBelgeError,
    get_api_key,
    get_base_url,
)
from services.ebelge.efatura_service import EFaturaService  # noqa: E402
from services.ebelge.eirsaliye_service import EIrsaliyeService  # noqa: E402
from services.ebelge.payload_mappers import (  # noqa: E402
    map_efatura_create_payload,
    map_eirsaliye_create_payload,
    validation_errors_for_efatura,
    validation_errors_for_eirsaliye,
)
from services.ebelge.turkcell_client import redact_headers  # noqa: E402


# ---------------------------------------------------------------------------
# Mock httpx
# ---------------------------------------------------------------------------

class _MockResponse:
    def __init__(
        self,
        status_code: int = 200,
        json_body: Optional[Dict[str, Any]] = None,
        text: Optional[str] = None,
        content: Optional[bytes] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        self.status_code = status_code
        self._json = json_body
        self._text = text or ""
        self.content = content or b""
        self.headers = headers or {"content-type": "application/json"}

    def json(self) -> Any:
        if self._json is None:
            raise ValueError("No JSON body")
        return self._json

    @property
    def text(self) -> str:
        return self._text


class _MockClient:
    """Mimics httpx.Client context manager."""

    def __init__(self, *, post_resp: Optional[_MockResponse] = None, get_resp: Optional[_MockResponse] = None) -> None:
        self._post_resp = post_resp
        self._get_resp = get_resp
        self.last_url: Optional[str] = None
        self.last_headers: Optional[Dict[str, str]] = None
        self.last_payload: Optional[Dict[str, Any]] = None

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def post(self, url, json=None, headers=None, **_kwargs):
        self.last_url = url
        self.last_headers = dict(headers or {})
        self.last_payload = json
        if self._post_resp is None:
            raise RuntimeError("No POST response configured")
        return self._post_resp

    def get(self, url, headers=None, **_kwargs):
        self.last_url = url
        self.last_headers = dict(headers or {})
        if self._get_resp is None:
            raise RuntimeError("No GET response configured")
        return self._get_resp


def _patch_httpx(monkeypatch: pytest.MonkeyPatch, client: _MockClient) -> _MockClient:
    import services.ebelge.turkcell_client as tc

    def _factory(*_args, **_kwargs):
        return client

    monkeypatch.setattr(tc.httpx, "Client", _factory)
    return client


# ===========================================================================
# Payload mapper tests
# ===========================================================================

def test_efatura_payload_mapper_calculates_vat_and_line_extension():
    payload = {
        "receiver": {
            "name": "Acme AŞ",
            "vkn": "1234567890",
            "alias": "urn:mail:defaultpk@acme.com",
            "district": "Kadıköy",
            "city": "İstanbul",
            "country": "Türkiye",
            "street": "Test Cad. No:5",
            "zip_code": "34000",
            "tax_office": "Kadıköy",
        },
        "invoice": {
            "issue_date": "2025-07-15",
            "prefix": "EPA",
            "currency": "TRY",
            "local_reference_id": "LOCAL-1",
            "note": "Test",
        },
        "lines": [
            {"name": "Süt", "quantity": 10, "unit_code": "NIU", "unit_price": 100, "vat_rate": 20},
        ],
    }
    result = map_efatura_create_payload(payload)

    assert result["recordType"] == 1
    assert result["localReferenceId"] == "LOCAL-1"
    assert result["addressBook"]["identificationNumber"] == "1234567890"
    assert result["generalInfoModel"]["prefix"] == "EPA"
    assert result["generalInfoModel"]["ettn"]  # generated uuid
    assert len(result["invoiceLines"]) == 1

    line = result["invoiceLines"][0]
    assert line["amount"] == 10
    assert line["unitPrice"] == 100
    assert line["lineExtensionAmount"] == 1000.0
    assert line["vatAmount"] == 200.0
    assert line["taxes"][0]["taxTypeCode"] == "0015"
    assert line["taxes"][0]["taxAmount"] == 200.0


def test_efatura_validation_errors_detect_missing_fields():
    errors = validation_errors_for_efatura({"receiver": {}, "invoice": {}, "lines": []})
    assert any("vkn" in err for err in errors)
    assert any("name" in err for err in errors)
    assert any("issue_date" in err for err in errors)
    assert any("lines" in err for err in errors)


def test_eirsaliye_payload_mapper_maps_shipment_and_delivery():
    payload = {
        "receiver": {"name": "Acme", "vkn": "1234567890", "city": "İstanbul"},
        "despatch": {"issue_date": "2025-07-15", "prefix": "EIR"},
        "delivery": {"street": "Teslimat Cad.", "city": "Ankara"},
        "shipment": {
            "plate_number": "34ABC123",
            "driver_name": "Ali",
            "driver_surname": "Veli",
            "driver_tckn": "12345678901",
        },
        "lines": [{"product_name": "Süt Kutusu", "quantity": 5, "unit_code": "C62", "unit_price": 50}],
    }
    result = map_eirsaliye_create_payload(payload)

    assert result["addressBook"]["name"] == "Acme"
    assert result["deliveryAddressInfo"]["receiverCity"] == "Ankara"
    assert result["despatchShipmentInfo"]["plateNumber"] == "34ABC123"
    assert result["despatchShipmentInfo"]["driverIdentificationNumber"] == "12345678901"
    assert len(result["despatchLines"]) == 1
    assert result["despatchLines"][0]["amount"] == 5


def test_eirsaliye_validation_errors():
    errors = validation_errors_for_eirsaliye({"receiver": {}, "despatch": {}, "lines": []})
    assert any("name" in err for err in errors)
    assert any("issue_date" in err for err in errors)


# ===========================================================================
# Turkcell client contract tests (mock HTTP)
# ===========================================================================

def test_client_uses_x_api_key_header(monkeypatch):
    mock = _MockClient(
        post_resp=_MockResponse(200, {"Id": "P-1", "InvoiceNumber": "INV-0001"})
    )
    _patch_httpx(monkeypatch, mock)

    client = TurkcellEBelgeClient(DocumentKind.EFATURA, api_key="secret-key")
    result = client.post_json("/v1/outboxinvoice/create", {"foo": "bar"})

    assert result["success"] is True
    assert result["provider_id"] == "P-1"
    assert result["document_number"] == "INV-0001"
    assert mock.last_headers is not None
    assert mock.last_headers.get("x-api-key") == "secret-key"


def test_client_success_parses_id_and_invoice_number(monkeypatch):
    mock = _MockClient(
        post_resp=_MockResponse(200, {"Id": "prov-abc", "InvoiceNumber": "EPA2025000001"})
    )
    _patch_httpx(monkeypatch, mock)

    service = EFaturaService(client=TurkcellEBelgeClient(DocumentKind.EFATURA, api_key="k"))
    result = service.create({"any": "payload"})

    assert result["provider_id"] == "prov-abc"
    assert result["document_number"] == "EPA2025000001"


def test_client_provider_error_400_is_parsed(monkeypatch):
    error_body = {
        "Error": {"title": "BusinessException", "detail": "VKN hatalı"},
        "traceId": "tr-999",
    }
    mock = _MockClient(post_resp=_MockResponse(400, error_body))
    _patch_httpx(monkeypatch, mock)

    client = TurkcellEBelgeClient(DocumentKind.EFATURA, api_key="k")
    with pytest.raises(TurkcellEBelgeError) as exc_info:
        client.post_json("/v1/outboxinvoice/create", {"foo": "bar"})

    err = exc_info.value
    assert err.status_code == 400
    assert err.provider_status == "BusinessException"
    assert "VKN hatalı" in err.message
    assert err.trace_id == "tr-999"


def test_client_status_endpoint(monkeypatch):
    mock = _MockClient(get_resp=_MockResponse(200, {"Status": "Accepted"}))
    _patch_httpx(monkeypatch, mock)

    service = EFaturaService(client=TurkcellEBelgeClient(DocumentKind.EFATURA, api_key="k"))
    result = service.status("prov-abc")

    assert result["success"] is True
    assert "outboxinvoice/prov-abc/status" in (mock.last_url or "")


def test_client_binary_pdf(monkeypatch):
    mock = _MockClient(
        get_resp=_MockResponse(
            200, content=b"%PDF-1.4 dummy", headers={"content-type": "application/pdf"}
        )
    )
    _patch_httpx(monkeypatch, mock)

    service = EFaturaService(client=TurkcellEBelgeClient(DocumentKind.EFATURA, api_key="k"))
    result = service.pdf("prov-abc")

    assert result["content"].startswith(b"%PDF")
    assert result["content_type"] == "application/pdf"
    assert "outboxinvoice/prov-abc/pdf/true" in (mock.last_url or "")


def test_api_key_missing_raises(monkeypatch):
    monkeypatch.delenv("TURKCELL_EBELGE_API_KEY", raising=False)
    monkeypatch.delenv("TURKCELL_X_API_KEY", raising=False)
    monkeypatch.delenv("TURKCELL_EINVOICE_API_KEY", raising=False)

    with pytest.raises(TurkcellEBelgeError) as exc_info:
        TurkcellEBelgeClient(DocumentKind.EFATURA)

    assert exc_info.value.status_code == 500
    assert "API key" in str(exc_info.value)


def test_legacy_fallback_key_is_respected(monkeypatch):
    monkeypatch.delenv("TURKCELL_EBELGE_API_KEY", raising=False)
    monkeypatch.delenv("TURKCELL_X_API_KEY", raising=False)
    monkeypatch.setenv("TURKCELL_EINVOICE_API_KEY", "legacy-xyz")

    assert get_api_key() == "legacy-xyz"


def test_base_url_selection(monkeypatch):
    monkeypatch.setenv("TURKCELL_EBELGE_ENV", "test")
    assert "efaturaservicetest" in get_base_url(DocumentKind.EFATURA)
    assert "eirsaliyeservicetest" in get_base_url(DocumentKind.EIRSALIYE)

    monkeypatch.setenv("TURKCELL_EBELGE_ENV", "prod")
    assert "turkcellesirket.com" in get_base_url(DocumentKind.EFATURA)
    assert "turkcellesirket.com" in get_base_url(DocumentKind.EIRSALIYE)


def test_redact_headers_drops_sensitive_values():
    headers = {
        "x-api-key": "super-secret",
        "Authorization": "Bearer abc",
        "Content-Type": "application/json",
    }
    redacted = redact_headers(headers)
    assert redacted["x-api-key"] == "***REDACTED***"
    assert redacted["Authorization"] == "***REDACTED***"
    assert redacted["Content-Type"] == "application/json"


def test_eirsaliye_create_hits_correct_path(monkeypatch):
    mock = _MockClient(
        post_resp=_MockResponse(200, {"Id": "des-1", "DespatchNumber": "DES-0001"})
    )
    _patch_httpx(monkeypatch, mock)

    service = EIrsaliyeService(client=TurkcellEBelgeClient(DocumentKind.EIRSALIYE, api_key="k"))
    result = service.create({"foo": "bar"})

    assert result["provider_id"] == "des-1"
    assert result["document_number"] == "DES-0001"
    assert "/v1/outboxdespatch/create" in (mock.last_url or "")
    assert "eirsaliyeservicetest" in (mock.last_url or "")


def test_eirsaliye_zip_endpoint(monkeypatch):
    mock = _MockClient(
        get_resp=_MockResponse(
            200, content=b"PK\x03\x04dummy", headers={"content-type": "application/zip"}
        )
    )
    _patch_httpx(monkeypatch, mock)

    service = EIrsaliyeService(client=TurkcellEBelgeClient(DocumentKind.EIRSALIYE, api_key="k"))
    result = service.zip("des-1")

    assert result["content"].startswith(b"PK")
    assert result["content_type"] == "application/zip"
    assert "/outboxdespatch/des-1/zip" in (mock.last_url or "")


def test_success_with_error_object_becomes_failure(monkeypatch):
    """HTTP 200 but Error object present => treated as failure (contract)."""
    body = {"Error": {"title": "Rejected", "detail": "Alıcı hatalı"}, "Id": None}
    mock = _MockClient(post_resp=_MockResponse(200, body))
    _patch_httpx(monkeypatch, mock)

    client = TurkcellEBelgeClient(DocumentKind.EFATURA, api_key="k")
    with pytest.raises(TurkcellEBelgeError) as exc_info:
        client.post_json("/v1/outboxinvoice/create", {})

    assert exc_info.value.provider_status == "Rejected"
    assert "Alıcı" in exc_info.value.message
