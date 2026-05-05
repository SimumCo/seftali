"""Shared Turkcell e-Şirket HTTP client for e-Fatura ve e-İrsaliye.

Highlights:
    * x-api-key header env'den okunur (TURKCELL_EBELGE_API_KEY; fallback TURKCELL_EINVOICE_API_KEY).
    * Secret (api key) asla log'a yazılmaz – `redact_headers` helper'ı uygulanır.
    * Provider response normalize edilir (success / http_status / provider_id / raw).
    * Timeout + lineer retry (transient 5xx + network error).
    * Gerçek provider'a bu modül içinden **otomatik test atılmaz** — testler mock'lanır.

Ortak response contract (dict):
    {
        "success": bool,
        "http_status": int,
        "provider_id": Optional[str],
        "document_number": Optional[str],
        "provider_status": Optional[str],
        "provider_message": Optional[str],
        "raw_provider_body": Any,  # log amaçlı (secret yok)
    }
"""

from __future__ import annotations

import logging
import os
import time
from enum import Enum
from typing import Any, Dict, Mapping, Optional, Tuple

import httpx

logger = logging.getLogger("ebelge.turkcell")

_SENSITIVE_HEADER_KEYS = {"x-api-key", "authorization", "cookie", "set-cookie", "proxy-authorization"}


class DocumentKind(str, Enum):
    """Supported document kinds."""

    EFATURA = "efatura"
    EIRSALIYE = "eirsaliye"
    # EARSIV = "earsiv"  # Kullanıcı onayı ile sonraki fazda eklenecek.


class TurkcellEBelgeError(Exception):
    """Raised when the provider returns a non-success response or the client cannot reach it."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int = 502,
        provider_status: Optional[str] = None,
        provider_body: Any = None,
        trace_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.provider_status = provider_status
        self.provider_body = provider_body
        self.trace_id = trace_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "status_code": self.status_code,
            "provider_status": self.provider_status,
            "trace_id": self.trace_id,
            "provider_body": self.provider_body,
        }


def redact_headers(headers: Mapping[str, str]) -> Dict[str, str]:
    """Drop/replace sensitive header values before logging."""
    redacted: Dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in _SENSITIVE_HEADER_KEYS:
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted


def get_api_key() -> Optional[str]:
    """Return active Turkcell e-Belge API key (new env first, legacy fallback)."""
    return (
        os.environ.get("TURKCELL_EBELGE_API_KEY")
        or os.environ.get("TURKCELL_X_API_KEY")
        or os.environ.get("TURKCELL_EINVOICE_API_KEY")
    )


def _env_flag_is_prod() -> bool:
    env_flag = (os.environ.get("TURKCELL_EBELGE_ENV") or "test").strip().lower()
    return env_flag in {"prod", "production", "live"}


def get_base_url(kind: DocumentKind) -> str:
    """Select base URL based on document kind and TURKCELL_EBELGE_ENV."""
    is_prod = _env_flag_is_prod()

    if kind == DocumentKind.EFATURA:
        if is_prod:
            url = (
                os.environ.get("TURKCELL_EINVOICE_PROD_BASE_URL")
                or "https://efaturaservice.turkcellesirket.com"
            )
        else:
            url = (
                os.environ.get("TURKCELL_EINVOICE_TEST_BASE_URL")
                or os.environ.get("TURKCELL_EINVOICE_BASE_URL")
                or "https://efaturaservicetest.isim360.com"
            )
    elif kind == DocumentKind.EIRSALIYE:
        if is_prod:
            url = (
                os.environ.get("TURKCELL_EIRSLIYE_PROD_BASE_URL")
                or "https://eirsaliyeservice.turkcellesirket.com"
            )
        else:
            url = (
                os.environ.get("TURKCELL_EIRSLIYE_TEST_BASE_URL")
                or "https://eirsaliyeservicetest.isim360.com"
            )
    else:
        raise TurkcellEBelgeError(f"Unsupported document kind: {kind}", status_code=500)

    return url.rstrip("/")


def _extract_trace_id(body: Any, headers: Mapping[str, str]) -> Optional[str]:
    if isinstance(body, dict):
        for key in ("traceId", "trace_id", "TraceId"):
            if key in body and body[key]:
                return str(body[key])
    for key, value in headers.items():
        if key.lower() in {"x-request-id", "x-correlation-id", "traceparent"}:
            return value
    return None


def _extract_provider_id(body: Any) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    for key in ("Id", "id", "invoiceId", "InvoiceId", "despatchId", "DespatchId", "documentId"):
        value = body.get(key)
        if value:
            return str(value)
    data = body.get("Data") or body.get("data")
    if isinstance(data, dict):
        return _extract_provider_id(data)
    return None


def _extract_document_number(body: Any) -> Optional[str]:
    if not isinstance(body, dict):
        return None
    for key in (
        "InvoiceNumber",
        "invoiceNumber",
        "DocumentNumber",
        "documentNumber",
        "DespatchNumber",
        "despatchNumber",
    ):
        value = body.get(key)
        if value:
            return str(value)
    data = body.get("Data") or body.get("data")
    if isinstance(data, dict):
        return _extract_document_number(data)
    return None


def _extract_provider_message(body: Any) -> Tuple[Optional[str], Optional[str]]:
    """Return (provider_status, provider_message) from a provider body."""
    if not isinstance(body, dict):
        if isinstance(body, str) and body.strip():
            return None, body.strip()[:500]
        return None, None

    provider_status: Optional[str] = None
    provider_message: Optional[str] = None

    error = body.get("Error") or body.get("error")
    if isinstance(error, dict):
        provider_status = error.get("title") or error.get("Title") or provider_status
        provider_message = error.get("detail") or error.get("Detail") or provider_message
    elif isinstance(error, str):
        provider_message = error

    if not provider_message:
        for key in ("message", "Message", "detail", "Detail"):
            if body.get(key):
                provider_message = str(body[key])
                break

    errors = body.get("errors") or body.get("Errors")
    if not provider_message and isinstance(errors, (list, dict)):
        try:
            provider_message = str(errors)[:500]
        except Exception:
            provider_message = None

    if not provider_status:
        for key in ("status", "Status", "title", "Title"):
            if body.get(key):
                provider_status = str(body[key])
                break

    return provider_status, provider_message


class TurkcellEBelgeClient:
    """Thin, provider-agnostic HTTP adapter for Turkcell e-Fatura / e-İrsaliye REST."""

    def __init__(
        self,
        kind: DocumentKind,
        *,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        retry_attempts: Optional[int] = None,
    ) -> None:
        self.kind = kind
        self.api_key = api_key or get_api_key()
        if not self.api_key:
            raise TurkcellEBelgeError(
                "Turkcell e-Belge API key missing (TURKCELL_EBELGE_API_KEY)",
                status_code=500,
                provider_status="config_error",
            )

        self.base_url = (base_url or get_base_url(kind)).rstrip("/")
        self.timeout_seconds = float(
            timeout_seconds
            if timeout_seconds is not None
            else os.environ.get("TURKCELL_EBELGE_TIMEOUT_SECONDS")
            or os.environ.get("TURKCELL_EINVOICE_TIMEOUT_SECONDS", "20")
        )
        self.retry_attempts = int(
            retry_attempts
            if retry_attempts is not None
            else os.environ.get("TURKCELL_EBELGE_RETRY_ATTEMPTS")
            or os.environ.get("TURKCELL_EINVOICE_RETRY_ATTEMPTS", "3")
        )
        if self.retry_attempts < 1:
            self.retry_attempts = 1

    def _headers(self, extra: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "x-api-key": self.api_key,
            "Accept": "application/json",
        }
        if extra:
            for key, value in extra.items():
                headers[key] = value
        return headers

    def _url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return f"{self.base_url}{path}"

    def _safe_log(self, level: int, message: str, **extra: Any) -> None:
        headers = extra.pop("headers", None)
        if headers is not None:
            extra["headers"] = redact_headers(headers)
        logger.log(level, "%s | %s", message, {k: v for k, v in extra.items() if k != "body"})

    def _parse_body(self, response: httpx.Response) -> Any:
        content_type = (response.headers.get("content-type") or "").lower()
        try:
            if "application/json" in content_type:
                return response.json()
        except Exception:
            pass
        # Binary responses (pdf/ubl/zip) are handled by caller.
        try:
            return response.json()
        except Exception:
            return response.text

    def post_json(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON payload (e.g. /v1/outboxinvoice/create, /v1/outboxdespatch/create)."""
        url = self._url(path)
        headers = self._headers({"Content-Type": "application/json"})

        last_exc: Optional[Exception] = None
        attempt = 0
        backoff = 0.5

        while attempt < self.retry_attempts:
            attempt += 1
            try:
                self._safe_log(
                    logging.INFO,
                    "ebelge.request",
                    method="POST",
                    url=url,
                    headers=headers,
                    attempt=attempt,
                )
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(url, json=payload, headers=headers)
                body = self._parse_body(response)
                return self._build_json_result(response, body)
            except httpx.HTTPError as exc:
                last_exc = exc
                self._safe_log(
                    logging.WARNING,
                    "ebelge.network_error",
                    url=url,
                    attempt=attempt,
                    error=str(exc),
                )
                if attempt >= self.retry_attempts:
                    break
                time.sleep(backoff * attempt)

        raise TurkcellEBelgeError(
            f"Provider not reachable: {last_exc}",
            status_code=502,
            provider_status="network_error",
        )

    def _build_json_result(self, response: httpx.Response, body: Any) -> Dict[str, Any]:
        status = response.status_code
        provider_status, provider_message = _extract_provider_message(body)
        provider_id = _extract_provider_id(body)
        document_number = _extract_document_number(body)
        trace_id = _extract_trace_id(body, response.headers)

        success = 200 <= status < 300

        # Business: 200 ama Error objesi varsa failure olarak kabul et.
        if success and isinstance(body, dict):
            if body.get("Error") or body.get("error"):
                success = False

        result: Dict[str, Any] = {
            "success": success,
            "http_status": status,
            "provider_id": provider_id,
            "document_number": document_number,
            "provider_status": provider_status or ("ok" if success else None),
            "provider_message": provider_message,
            "raw_provider_body": body,
            "trace_id": trace_id,
        }

        if not success:
            raise TurkcellEBelgeError(
                provider_message or f"Provider error (HTTP {status})",
                status_code=status if 400 <= status < 600 else 502,
                provider_status=provider_status,
                provider_body=body,
                trace_id=trace_id,
            )

        return result

    def get_json(self, path: str) -> Dict[str, Any]:
        """GET JSON (e.g. status endpoint)."""
        url = self._url(path)
        headers = self._headers()
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise TurkcellEBelgeError(
                f"Provider not reachable: {exc}",
                status_code=502,
                provider_status="network_error",
            ) from exc

        body = self._parse_body(response)
        return self._build_json_result(response, body)

    def get_binary(self, path: str, *, expected_content_type: Optional[str] = None) -> Dict[str, Any]:
        """GET binary or text payload (html/pdf/ubl/zip).

        Returns:
            {
                "content": bytes,
                "content_type": str,
                "http_status": int,
            }
        """
        url = self._url(path)
        headers = self._headers()
        if expected_content_type:
            headers["Accept"] = expected_content_type
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.get(url, headers=headers)
        except httpx.HTTPError as exc:
            raise TurkcellEBelgeError(
                f"Provider not reachable: {exc}",
                status_code=502,
                provider_status="network_error",
            ) from exc

        if not (200 <= response.status_code < 300):
            body = self._parse_body(response)
            provider_status, provider_message = _extract_provider_message(body)
            raise TurkcellEBelgeError(
                provider_message or f"Provider error (HTTP {response.status_code})",
                status_code=response.status_code,
                provider_status=provider_status,
                provider_body=body,
            )

        return {
            "content": response.content,
            "content_type": response.headers.get("content-type", "application/octet-stream"),
            "http_status": response.status_code,
        }


def build_client_for(kind: DocumentKind) -> TurkcellEBelgeClient:
    return TurkcellEBelgeClient(kind)
