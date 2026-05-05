"""
Turkcell e-Fatura JSON v1 outbox provider adapter.

Target endpoint: POST {TURKCELL_EINVOICE_BASE_URL}{TURKCELL_OUTBOX_CREATE_PATH}
(default path: /v1/outboxinvoice/create)

Authentication: header `x-api-key` sourced from env only (never exposed).
"""
from __future__ import annotations

import asyncio
import logging
import os
from decimal import Decimal
from typing import Any, Dict, Optional

import httpx
from dotenv import dotenv_values

logger = logging.getLogger(__name__)

# Redaction helpers (keep them local so no sensitive header leaks into logs)
_SENSITIVE_HEADER_KEYS = {'x-api-key', 'authorization', 'cookie', 'set-cookie'}


def _redact_headers(headers: Dict[str, str]) -> Dict[str, str]:
    """Return a copy with sensitive header values masked."""
    redacted = {}
    for key, value in (headers or {}).items():
        if key.lower() in _SENSITIVE_HEADER_KEYS:
            redacted[key] = '***redacted***'
        else:
            redacted[key] = value
    return redacted


class OutboxProviderError(Exception):
    """
    Raised when provider call fails (network, auth, validation).

    Attributes:
        message: English technical message
        status_code: HTTP status to bubble up (422 validation, 401/403 auth, 504 timeout, ...)
        provider_code: Best-effort error code extracted from provider body
        provider_message: Best-effort human message extracted from provider body
        raw_payload: Full provider body (dict or {'raw_text': ...})
        validation_hints: List[str] — user-friendly hints parsed from provider body
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 500,
        provider_code: Optional[str] = None,
        provider_message: Optional[str] = None,
        raw_payload: Any = None,
        validation_hints: Optional[list] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.provider_code = provider_code
        self.provider_message = provider_message or message
        self.raw_payload = raw_payload
        self.validation_hints = validation_hints or []


class TurkcellOutboxProvider:
    """
    Thin, JSON-only adapter for the v1 outboxinvoice/create endpoint.

    Distinct from `TurkcellEFaturaProviderAdapter` (which speaks UBL/multipart on /v2).
    """

    DEFAULT_CREATE_PATH = '/v1/outboxinvoice/create'

    def __init__(self, http_client_factory=None):
        env = dotenv_values('/app/backend/.env')

        def _env(key: str, default: Optional[str] = None) -> Optional[str]:
            return os.environ.get(key) or env.get(key) or default

        # Full URL override takes priority; otherwise base_url + path
        full_url = _env('TURKCELL_OUTBOX_CREATE_URL')
        if full_url:
            self.create_url = full_url
        else:
            base = (_env('TURKCELL_EINVOICE_BASE_URL') or '').rstrip('/')
            path = _env('TURKCELL_OUTBOX_CREATE_PATH', self.DEFAULT_CREATE_PATH) or self.DEFAULT_CREATE_PATH
            if not base:
                raise OutboxProviderError('Turkcell outbox configuration missing (BASE_URL)', status_code=500)
            self.create_url = f"{base}/{path.lstrip('/')}"

        # API key: new env name preferred, legacy name fallback
        self.api_key = _env('TURKCELL_X_API_KEY') or _env('TURKCELL_EINVOICE_API_KEY')
        if not self.api_key:
            raise OutboxProviderError('Turkcell outbox API key missing (TURKCELL_X_API_KEY)', status_code=500)

        self.timeout_seconds = float(_env('TURKCELL_OUTBOX_TIMEOUT_SECONDS', _env('TURKCELL_EINVOICE_TIMEOUT_SECONDS', '20')))
        self.retry_attempts = int(_env('TURKCELL_OUTBOX_RETRY_ATTEMPTS', _env('TURKCELL_EINVOICE_RETRY_ATTEMPTS', '3')))
        self._http_client_factory = http_client_factory

    # ----- headers -----
    def _headers(self) -> Dict[str, str]:
        return {
            'x-api-key': self.api_key,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    # ----- http -----
    async def _request(self, url: str, json_body: Dict[str, Any]) -> httpx.Response:
        last_error: Optional[OutboxProviderError] = None
        safe_headers = _redact_headers(self._headers())
        logger.info(
            'turkcell_outbox_request',
            extra={
                'route': 'outbox_create',
                'url': url,
                'headers': safe_headers,
                'payload_keys': list(json_body.keys()) if isinstance(json_body, dict) else None,
            },
        )
        for attempt in range(max(1, self.retry_attempts)):
            try:
                if self._http_client_factory:
                    client_cm = self._http_client_factory()
                else:
                    client_cm = httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True)
                async with client_cm as client:
                    response = await client.post(url, json=json_body, headers=self._headers())
                    return response
            except httpx.TimeoutException:
                last_error = OutboxProviderError('Provider timeout', status_code=504)
            except httpx.HTTPError as exc:
                last_error = OutboxProviderError(f'Provider request failed: {type(exc).__name__}', status_code=503)
            if attempt < self.retry_attempts - 1:
                await asyncio.sleep(min(2 ** attempt, 8))
        raise last_error or OutboxProviderError('Provider request failed', status_code=503)

    # ----- public API -----
    async def create_outbox_invoice(self, provider_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        POSTs a JSON body to v1/outboxinvoice/create and returns a normalized dict.

        Raises OutboxProviderError on any failure. Never returns an error payload.
        """
        response = await self._request(self.create_url, provider_body)
        body = self._parse_body(response)

        if response.status_code == 422:
            raise OutboxProviderError(
                'Provider validation error',
                status_code=422,
                provider_code=self._extract_code(body),
                provider_message=self._extract_message(body),
                raw_payload=body,
                validation_hints=self._extract_validation_hints(body),
            )
        if response.status_code in {401, 403}:
            # NEVER log the api key; we only log the redacted header on request path
            raise OutboxProviderError(
                'Provider authentication failed',
                status_code=response.status_code,
                provider_code=self._extract_code(body),
                provider_message=self._extract_message(body),
                raw_payload=body,
            )
        if response.status_code == 404:
            raise OutboxProviderError(
                'Provider endpoint not found',
                status_code=404,
                provider_code=self._extract_code(body),
                provider_message=self._extract_message(body),
                raw_payload=body,
            )
        if response.status_code >= 400:
            raise OutboxProviderError(
                'Provider request failed',
                status_code=response.status_code,
                provider_code=self._extract_code(body),
                provider_message=self._extract_message(body),
                raw_payload=body,
                validation_hints=self._extract_validation_hints(body),
            )

        return {
            'http_status': response.status_code,
            'id': self._extract_id(body),
            'invoice_number': self._extract_invoice_number(body),
            'provider_status': self._extract_provider_status(body),
            'provider_body': body,
        }

    # ----- parsing helpers -----
    @staticmethod
    def _parse_body(response: httpx.Response) -> Dict[str, Any]:
        content_type = (response.headers.get('content-type') or '').lower()
        if 'application/json' in content_type:
            try:
                return response.json()
            except Exception:
                return {'raw_text': response.text}
        return {'raw_text': response.text}

    @staticmethod
    def _extract_id(body: Any) -> Optional[str]:
        if not isinstance(body, dict):
            return None
        for key in ['Id', 'id', 'invoiceId', 'InvoiceId', 'providerInvoiceId', 'ettn', 'uuid', 'UUID']:
            value = body.get(key)
            if value:
                return str(value)
        # Some providers wrap in {"data": {...}}
        data = body.get('data') or body.get('Data')
        if isinstance(data, dict):
            for key in ['Id', 'id', 'invoiceId', 'InvoiceId', 'ettn', 'uuid']:
                value = data.get(key)
                if value:
                    return str(value)
        return None

    @staticmethod
    def _extract_invoice_number(body: Any) -> Optional[str]:
        if not isinstance(body, dict):
            return None
        for key in ['InvoiceNumber', 'invoiceNumber', 'invoice_number', 'Number', 'number']:
            value = body.get(key)
            if value:
                return str(value)
        data = body.get('data') or body.get('Data')
        if isinstance(data, dict):
            for key in ['InvoiceNumber', 'invoiceNumber', 'invoice_number', 'number']:
                value = data.get(key)
                if value:
                    return str(value)
        return None

    @staticmethod
    def _extract_provider_status(body: Any) -> Optional[str]:
        if not isinstance(body, dict):
            return None
        for key in ['status', 'Status', 'invoiceStatus', 'envelopeStatus', 'state', 'result']:
            value = body.get(key)
            if value is not None:
                return str(value)
        return None

    @staticmethod
    def _extract_code(body: Any) -> Optional[str]:
        if not isinstance(body, dict):
            return None
        error = body.get('Error') or body.get('error')
        if isinstance(error, dict):
            for key in ['code', 'statusCode', 'errorCode']:
                if error.get(key) is not None:
                    return str(error.get(key))
        for key in ['statusCode', 'status_code', 'code', 'errorCode']:
            if body.get(key) is not None:
                return str(body.get(key))
        return None

    @staticmethod
    def _extract_message(body: Any) -> Optional[str]:
        if not isinstance(body, dict):
            return None
        error = body.get('Error') or body.get('error')
        if isinstance(error, dict):
            for key in ['detail', 'title', 'message', 'description']:
                value = error.get(key)
                if value:
                    return str(value)
        for key in ['message', 'detail', 'statusMessage', 'errorMessage', 'title']:
            value = body.get(key)
            if value:
                return str(value)
        # Fallback to truncated stringify
        return str(body)[:500]

    @staticmethod
    def _extract_validation_hints(body: Any) -> list:
        """Pull user-visible validation hints from various common shapes."""
        hints: list = []
        if not isinstance(body, dict):
            return hints
        error = body.get('Error') or body.get('error')
        if isinstance(error, dict):
            title = error.get('title') or error.get('Title')
            detail = error.get('detail') or error.get('Detail')
            if title:
                hints.append(str(title))
            if detail and str(detail) != str(title):
                hints.append(str(detail))
        # Shape A: "errors": [{"field": "...", "message": "..."}] or {"field": ["msg", ...]}
        errors = body.get('errors') or body.get('Errors') or body.get('validationErrors')
        if isinstance(errors, list):
            for item in errors:
                if isinstance(item, dict):
                    field = item.get('field') or item.get('path') or item.get('propertyName')
                    msg = item.get('message') or item.get('errorMessage') or item.get('detail')
                    if field and msg:
                        hints.append(f"{field}: {msg}")
                    elif msg:
                        hints.append(str(msg))
                elif isinstance(item, str):
                    hints.append(item)
        elif isinstance(errors, dict):
            for field, value in errors.items():
                if isinstance(value, list):
                    for v in value:
                        hints.append(f"{field}: {v}")
                else:
                    hints.append(f"{field}: {value}")
        # Shape B (Turkcell v1): root-level {"fieldName": ["error1", "error2"], ...}
        # Activate only if there's no structured "message/detail" pattern at root.
        if not hints and isinstance(body, dict):
            reserved_keys = {
                'Id', 'id', 'InvoiceNumber', 'invoiceNumber', 'status', 'Status',
                'message', 'detail', 'statusMessage', 'title', 'Error', 'error',
                'data', 'Data', 'code', 'statusCode', 'invoiceStatus', 'envelopeStatus',
                'raw_text', 'ettn', 'uuid',
            }
            for field, value in body.items():
                if field in reserved_keys:
                    continue
                if isinstance(value, list) and value and all(isinstance(v, str) for v in value):
                    for v in value:
                        hints.append(f"{field}: {v}")
        # Top-level message as last-resort hint
        top_msg = body.get('message') or body.get('detail')
        if top_msg and not hints:
            hints.append(str(top_msg))
        return hints


# ---- Frontend payload → Turkcell body mapper ----
def _money(value: Decimal, places: str = '0.01') -> str:
    return str(Decimal(value).quantize(Decimal(places)))


# Turkcell v1 enum: generalInfoModel.Type
INVOICE_TYPE_ENUM = {
    'SATIS': 1, 'IADE': 2, 'ISTISNA': 3, 'OZELMATRAH': 4, 'TEVKIFAT': 5,
    'ARACTESCIL': 6, 'IHRACKAYITLI': 7, 'SGK': 8, 'KOMISYONCU': 9,
    'SERBESTMESLEKMAKBUZU': 10, 'MUSTAHSILMAKBUZ': 11, 'HKSSATIS': 12,
    'HKSKOMISYONCU': 13, 'STANDARTKODLU': 14, 'TEVKIFATIADE': 15,
    'KONAKLAMAVERGISI': 17, 'SARJ': 18, 'SARJANLIK': 19, 'TEKNOLOJIDESTEK': 20,
    'ADISYON': 21, 'YTBSATIS': 22, 'YTBISTISNA': 23, 'YTBIADE': 24,
    'YTBTEVKIFAT': 25, 'YTBTEVKIFATIADE': 26,
}

# Turkcell v1 enum: generalInfoModel.InvoiceProfileType
INVOICE_PROFILE_ENUM = {
    'TEMELFATURA': 1,
    'TICARIFATURA': 2,
    'TICARI': 2,
    'IHRACAT': 3,
    'YOLCUBERABERFATURA': 4,
    'KAMU': 5,
    'EARSIVFATURA': 6,
    'HKSFATURA': 7,
}

# Turkcell v1 accepts UBL/UN-CEFACT unit codes. If the caller passes a Turkish
# keyword (or a commonly-used non-UBL synonym), we translate to the UBL equivalent.
UNIT_CODE_MAP = {
    # Turkish keywords → UBL
    'ADET': 'C62',
    'ADET(K)': 'C62',
    'ADT': 'C62',
    'TANE': 'C62',
    'KG': 'KGM',
    'KILOGRAM': 'KGM',
    'GRAM': 'GRM',
    'GR': 'GRM',
    'LITRE': 'LTR',
    'LT': 'LTR',
    'METRE': 'MTR',
    'MT': 'MTR',
    'METREKARE': 'MTK',
    'M2': 'MTK',
    'METREKUP': 'MTQ',
    'M3': 'MTQ',
    'TON': 'TNE',
    'KOLI': 'CT',
    'KUTU': 'BX',
    'PAKET': 'PK',
    'CIFT': 'PR',
    # Common non-UBL synonyms Turkcell v1 rejects → normalize to UBL
    'NIU': 'C62',
    'EA': 'C62',
    'PCE': 'C62',
    'PC': 'C62',
    'H87': 'H87',
    'C62': 'C62',
}


def _resolve_unit_code(value: Any) -> str:
    """Return a Turkcell v1-accepted unit code (UBL codes, default C62)."""
    if not value:
        return 'C62'
    svalue = str(value).strip().upper()
    return UNIT_CODE_MAP.get(svalue, svalue)


def _resolve_type(value: Any, enum: Dict[str, int], default: int) -> int:
    """Accept int, int-as-string, or enum name; fall back to default."""
    if value is None:
        return default
    if isinstance(value, int):
        return value
    svalue = str(value).strip().upper()
    if svalue.isdigit():
        return int(svalue)
    return enum.get(svalue, default)


def map_request_to_provider_body(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert our flat OutboxCreateRequest dict to the Turkcell v1
    (/v1/outboxinvoice/create) JSON shape.

    Turkcell v1 expects: addressBook, generalInfoModel, invoiceLines,
    (optional companyInformation), localReferenceId.

    Callers needing full control can send `raw_provider_body` to bypass mapping.
    """
    if payload.get('raw_provider_body'):
        return dict(payload['raw_provider_body'])

    receiver = payload.get('receiver') or {}
    supplier = payload.get('supplier')
    lines = payload.get('lines') or []

    def _address_book(party: Dict[str, Any]) -> Dict[str, Any]:
        address = party.get('address') or {}
        return {
            'IdentificationNumber': party.get('vkn_tckn'),
            'Name': party.get('title'),
            'Alias': party.get('alias'),
            'TaxOffice': party.get('tax_office'),
            'ReceiverCountry': address.get('country') or 'Türkiye',
            'ReceiverCity': address.get('city'),
            'ReceiverDistrict': address.get('district') or address.get('city'),
            'ReceiverStreet': address.get('street'),
            'ReceiverPostalCode': address.get('postal_code'),
        }

    invoice_type_value = _resolve_type(payload.get('invoice_type_code'), INVOICE_TYPE_ENUM, 1)
    profile_type_value = _resolve_type(payload.get('scenario'), INVOICE_PROFILE_ENUM, 1)
    currency = (payload.get('document_currency_code') or 'TRY').upper() or 'TRY'

    general_info: Dict[str, Any] = {
        'Type': invoice_type_value,
        'InvoiceProfileType': profile_type_value,
        'CurrencyCode': currency,
        'IssueDate': payload.get('issue_date'),
        'ExchangeRate': 1,
    }
    if payload.get('notes'):
        general_info['Notes'] = payload['notes']

    invoice_lines = []
    for line in lines:
        line_body: Dict[str, Any] = {
            'InventoryCard': line.get('name'),
            'Name': line.get('name'),
            'Amount': _money(line.get('quantity'), '0.0001'),
            'UnitCode': _resolve_unit_code(line.get('unit_code')),
            'UnitPrice': _money(line.get('unit_price')),
            'VatRate': _money(line.get('vat_rate')),
        }
        if line.get('discount_rate') is not None:
            line_body['DiscountRate'] = _money(line.get('discount_rate'))
        if line.get('note'):
            line_body['Note'] = line['note']
        invoice_lines.append(line_body)

    body: Dict[str, Any] = {
        'localReferenceId': payload.get('local_reference_id'),
        'addressBook': _address_book(receiver),
        'generalInfoModel': general_info,
        'invoiceLines': invoice_lines,
    }
    if supplier:
        body['companyInformation'] = _address_book(supplier)
    if payload.get('extra'):
        # Shallow-merge extras so caller can add provider-specific fields
        for key, value in payload['extra'].items():
            body[key] = value
    return body
