"""e-Fatura servisleri (Turkcell e-Şirket).

Endpoint mapping:
    POST /v1/outboxinvoice/create
    GET  /v2/outboxinvoice/{id}/status
    GET  /v2/outboxinvoice/{id}/html/{isStandartXslt}
    GET  /v2/outboxinvoice/{id}/pdf/{isStandartXslt}
    GET  /v2/outboxinvoice/{id}/ubl
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .turkcell_client import DocumentKind, TurkcellEBelgeClient


class EFaturaService:
    def __init__(self, client: Optional[TurkcellEBelgeClient] = None) -> None:
        self.client = client or TurkcellEBelgeClient(DocumentKind.EFATURA)

    # ---------- CREATE ----------
    def create(self, provider_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.client.post_json("/v1/outboxinvoice/create", provider_payload)

    # ---------- STATUS ----------
    def status(self, provider_id: str) -> Dict[str, Any]:
        return self.client.get_json(f"/v2/outboxinvoice/{provider_id}/status")

    # ---------- HTML ----------
    def html(self, provider_id: str, is_standart_xslt: bool = True) -> Dict[str, Any]:
        flag = "true" if is_standart_xslt else "false"
        return self.client.get_binary(
            f"/v2/outboxinvoice/{provider_id}/html/{flag}",
            expected_content_type="text/html",
        )

    # ---------- PDF ----------
    def pdf(self, provider_id: str, is_standart_xslt: bool = True) -> Dict[str, Any]:
        flag = "true" if is_standart_xslt else "false"
        return self.client.get_binary(
            f"/v2/outboxinvoice/{provider_id}/pdf/{flag}",
            expected_content_type="application/pdf",
        )

    # ---------- UBL ----------
    def ubl(self, provider_id: str) -> Dict[str, Any]:
        return self.client.get_binary(
            f"/v2/outboxinvoice/{provider_id}/ubl",
            expected_content_type="application/xml",
        )
