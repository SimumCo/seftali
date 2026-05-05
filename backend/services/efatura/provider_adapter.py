import os
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from dotenv import dotenv_values


class ProviderError(Exception):
    def __init__(self, message: str, *, status_code: int = 500, provider_code: Optional[str] = None, provider_message: Optional[str] = None, raw_payload=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.provider_code = provider_code
        self.provider_message = provider_message or message
        self.raw_payload = raw_payload


class TurkcellEFaturaProviderAdapter:
    def __init__(self):
        env = dotenv_values('/app/backend/.env')
        self.base_url = os.environ.get('TURKCELL_EINVOICE_BASE_URL') or env.get('TURKCELL_EINVOICE_BASE_URL')
        self.create_path = os.environ.get('TURKCELL_EINVOICE_CREATE_PATH') or env.get('TURKCELL_EINVOICE_CREATE_PATH')
        self.status_path = os.environ.get('TURKCELL_EINVOICE_STATUS_PATH') or env.get('TURKCELL_EINVOICE_STATUS_PATH')
        self.status_id_param = os.environ.get('TURKCELL_EINVOICE_STATUS_ID_PARAM') or env.get('TURKCELL_EINVOICE_STATUS_ID_PARAM', 'providerInvoiceId')
        self.api_key = os.environ.get('TURKCELL_EINVOICE_API_KEY') or env.get('TURKCELL_EINVOICE_API_KEY')
        self.timeout_seconds = float(os.environ.get('TURKCELL_EINVOICE_TIMEOUT_SECONDS') or env.get('TURKCELL_EINVOICE_TIMEOUT_SECONDS', '20'))
        self.retry_attempts = int(os.environ.get('TURKCELL_EINVOICE_RETRY_ATTEMPTS') or env.get('TURKCELL_EINVOICE_RETRY_ATTEMPTS', '3'))
        if not self.base_url or not self.create_path or not self.status_path:
            raise ProviderError('Turkcell e-Fatura provider configuration is incomplete', status_code=500)
        if not self.api_key:
            raise ProviderError('Turkcell e-Fatura API key is missing', status_code=500)

    def _headers(self):
        return {
            'x-api-key': self.api_key,
        }

    def _build_url(self, path: str):
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    async def _request(self, method: str, url: str, **kwargs):
        last_error = None
        for attempt in range(self.retry_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds, follow_redirects=True) as client:
                    response = await client.request(method, url, **kwargs)
                    return response
            except httpx.TimeoutException:
                last_error = ProviderError('Provider timeout', status_code=504)
            except httpx.HTTPError:
                last_error = ProviderError('Provider request failed', status_code=503)
            await asyncio.sleep(min(2 ** attempt, 8))
        raise last_error or ProviderError('Provider request failed', status_code=503)

    async def createInvoiceFromUbl(self, xml: str, metadata: dict):
        url = self._build_url(self.create_path)
        files = {
            'invoiceFile': ('invoice.xml', xml.encode('utf-8'), 'text/xml'),
        }
        data = {
            'appType': '1',
            'status': '20',
            'useManualInvoiceId': 'false',
            'targetAlias': metadata.get('receiver_alias') or 'urn:mail:defaulttest3pk@medyasoft.com.tr',
            'useFirstAlias': 'true',
            'prefix': 'EPA',
            'localReferenceId': metadata.get('local_reference_id'),
            'checkLocalReferenceId': 'false',
            'xsltCode': 'code',
        }
        response = await self._request('POST', url, files=files, data=data, headers=self._headers())
        payload = self._parse_response_payload(response)
        if response.status_code == 422:
            raise ProviderError('Provider business validation error', status_code=422, provider_code=self._extract_status_code(payload), provider_message=self._extract_status_message(payload), raw_payload=payload)
        if response.status_code in {401, 403}:
            raise ProviderError('Provider authentication failed', status_code=response.status_code, provider_code=self._extract_status_code(payload), provider_message=self._extract_status_message(payload), raw_payload=payload)
        if response.status_code == 404:
            raise ProviderError('Provider endpoint not found', status_code=404, provider_code=self._extract_status_code(payload), provider_message=self._extract_status_message(payload), raw_payload=payload)
        if response.status_code >= 400:
            raise ProviderError('Provider request failed', status_code=400, provider_code=self._extract_status_code(payload), provider_message=self._extract_status_message(payload), raw_payload=payload)
        return {
            'http_status': response.status_code,
            'payload': payload,
            'provider_invoice_id': self._extract_provider_invoice_id(payload),
            'invoice_number': self._extract_invoice_number(payload),
            'provider_status_code': self._extract_status_code(payload),
            'provider_status_message': self._extract_status_message(payload),
            'normalized_status': self.normalize_create_status(response.status_code, payload),
        }

    async def getInvoiceStatus(self, providerInvoiceId: str):
        status_path = self.status_path.replace('{id}', str(providerInvoiceId)) if '{id}' in self.status_path else self.status_path
        url = self._build_url(status_path)
        request_kwargs = {'headers': self._headers()}
        if '{id}' not in self.status_path:
            request_kwargs['params'] = {self.status_id_param: providerInvoiceId}
        response = await self._request('GET', url, **request_kwargs)
        payload = self._parse_response_payload(response)
        if response.status_code in {401, 403}:
            raise ProviderError('Provider authentication failed', status_code=response.status_code, provider_code=self._extract_status_code(payload), provider_message=self._extract_status_message(payload), raw_payload=payload)
        if response.status_code == 404:
            raise ProviderError('Provider status endpoint not found', status_code=404, provider_code=self._extract_status_code(payload), provider_message=self._extract_status_message(payload), raw_payload=payload)
        if response.status_code >= 400:
            raise ProviderError('Provider status request failed', status_code=response.status_code, provider_code=self._extract_status_code(payload), provider_message=self._extract_status_message(payload), raw_payload=payload)
        return {
            'http_status': response.status_code,
            'payload': payload,
            'provider_invoice_id': self._extract_provider_invoice_id(payload) or providerInvoiceId,
            'invoice_number': self._extract_invoice_number(payload),
            'provider_status_code': self._extract_status_code(payload),
            'provider_status_message': self._extract_status_message(payload),
            'normalized_status': self.normalize_status_payload(payload),
        }

    def normalize_create_status(self, http_status: int, payload):
        normalized = self.normalize_status_payload(payload)
        if normalized in {'sent', 'failed'}:
            return normalized
        return 'queued' if http_status in {200, 201, 202} else 'processing'

    def normalize_status_payload(self, payload):
        haystack = str(payload).lower()
        explicit_values = []
        if isinstance(payload, dict):
            for key in ['status', 'invoiceStatus', 'invoice_status', 'envelopeStatus', 'envelope_status', 'state', 'result']:
                value = payload.get(key)
                if value is not None:
                    explicit_values.append(str(value).lower())

        joined = ' '.join(explicit_values + [haystack])
        if any(token in joined for token in ['failed', 'error', 'rejected', 'reject', 'hata', 'red']):
            return 'failed'
        if any(token in joined for token in ['sent', 'accepted', 'completed', 'success', 'başarılı', 'basarili', 'delivered', 'gönderildi', 'gonderildi']):
            return 'sent'
        if any(token in joined for token in ['processing', 'process', 'pending', 'queued', 'created', 'received', 'hazırlanıyor', 'hazirlaniyor', 'inprogress', 'in_progress']):
            return 'processing'
        return 'processing'

    def next_poll_delay_seconds(self, attempt_count: int):
        if attempt_count <= 0:
            return 10
        if attempt_count == 1:
            return 30
        return 60

    def _parse_response_payload(self, response: httpx.Response):
        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            return response.json()
        return {'raw_text': response.text}

    def _extract_provider_invoice_id(self, payload):
        if isinstance(payload, dict):
            for key in ['providerInvoiceId', 'provider_invoice_id', 'invoiceId', 'invoice_id', 'InvoiceId', 'Id', 'id', 'uuid', 'ettn']:
                if payload.get(key):
                    return payload.get(key)
        return None

    def _extract_invoice_number(self, payload):
        if isinstance(payload, dict):
            for key in ['invoiceNumber', 'InvoiceNumber', 'invoice_number', 'number']:
                if payload.get(key):
                    return payload.get(key)
        return None

    def _extract_status_code(self, payload):
        if isinstance(payload, dict):
            for key in ['statusCode', 'status_code', 'code', 'errorCode']:
                if payload.get(key) is not None:
                    return str(payload.get(key))
        return None

    def _extract_status_message(self, payload):
        if isinstance(payload, dict):
            for key in ['statusMessage', 'status_message', 'message', 'errorMessage', 'detail']:
                if payload.get(key):
                    return str(payload.get(key))
        return str(payload)[:1000]
