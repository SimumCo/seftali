"""Request/response contracts for Turkcell v1 outboxinvoice/create JSON endpoint."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OutboxAddress(BaseModel):
    street: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = 'Türkiye'


class OutboxParty(BaseModel):
    """Receiver or supplier identification block."""
    vkn_tckn: str
    title: str
    alias: Optional[str] = None
    tax_office: Optional[str] = None
    address: Optional[OutboxAddress] = None

    @field_validator('vkn_tckn')
    @classmethod
    def _validate_vkn(cls, value: str) -> str:
        digits = ''.join(ch for ch in str(value) if ch.isdigit())
        if len(digits) not in {10, 11}:
            raise ValueError('vkn_tckn must be 10 or 11 digits')
        return digits


class OutboxLine(BaseModel):
    name: str
    quantity: Decimal
    unit_code: str = 'NIU'
    unit_price: Decimal
    vat_rate: Decimal = Decimal('0')
    discount_rate: Optional[Decimal] = None
    note: Optional[str] = None

    @field_validator('quantity', 'unit_price')
    @classmethod
    def _positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError('quantity and unit_price must be positive')
        return value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)

    @field_validator('vat_rate')
    @classmethod
    def _non_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError('vat_rate must be non-negative')
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class OutboxCreateRequest(BaseModel):
    """
    Minimal frontend-facing JSON payload for Turkcell v1/outboxinvoice/create.

    Required: local_reference_id, issue_date, receiver, lines
    Optional: supplier (defaults from env), scenario, invoice_type_code, currency, notes, extra, raw_provider_body
    """
    model_config = ConfigDict(extra='ignore')

    local_reference_id: str = Field(..., min_length=1, max_length=64)
    issue_date: date
    scenario: str = 'TEMELFATURA'
    invoice_type_code: str = 'SATIS'
    document_currency_code: str = 'TRY'

    receiver: OutboxParty
    supplier: Optional[OutboxParty] = None  # defaults from env

    lines: List[OutboxLine] = Field(..., min_length=1)
    notes: Optional[List[str]] = None

    # Arbitrary provider-specific extras (merged into provider body)
    extra: Optional[Dict[str, Any]] = None
    # Full passthrough: if provided, sent as-is; our mapping is skipped
    raw_provider_body: Optional[Dict[str, Any]] = None


class OutboxCreateResult(BaseModel):
    """Normalized response returned to the client."""
    id: Optional[str] = None
    invoice_number: Optional[str] = None
    provider_status: Optional[str] = None
    local_reference_id: str
    http_status: int
    provider_body: Dict[str, Any]
