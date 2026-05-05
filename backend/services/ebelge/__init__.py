"""E-Belge (Turkcell e-Şirket) integration package.

Bu paket mevcut services/efatura (UBL v2 upload) yapısını etkilemez.
Yeni Turkcell e-Şirket JSON create + status/html/pdf/ubl(/zip) akışlarını
additive olarak sunar:
  - e-Fatura (/v1/outboxinvoice/create)
  - e-İrsaliye (/v1/outboxdespatch/create)
"""

from .turkcell_client import (
    TurkcellEBelgeClient,
    TurkcellEBelgeError,
    DocumentKind,
    build_client_for,
    get_api_key,
    get_base_url,
)

__all__ = [
    "TurkcellEBelgeClient",
    "TurkcellEBelgeError",
    "DocumentKind",
    "build_client_for",
    "get_api_key",
    "get_base_url",
]
