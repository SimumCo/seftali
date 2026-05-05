"""Pydantic request/response schemas for /api/ebelge/* routes."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReceiverPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    vkn: Optional[str] = None
    tckn: Optional[str] = None
    alias: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Türkiye"
    street: Optional[str] = None
    zip_code: Optional[str] = None
    tax_office: Optional[str] = None


class InvoiceMetaPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: Optional[int] = 0
    local_reference_id: Optional[str] = None
    note: Optional[str] = None
    profile_type: Optional[int] = 0
    type: Optional[int] = 1
    issue_date: str
    prefix: Optional[str] = "EPA"
    currency: Optional[str] = "TRY"
    exchange_rate: Optional[float] = 1


class InvoiceLinePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    description: Optional[str] = None
    quantity: float = Field(gt=0)
    unit_code: Optional[str] = "NIU"
    unit_price: float = Field(ge=0)
    vat_rate: Optional[float] = 20


class EFaturaCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    receiver: ReceiverPayload
    invoice: InvoiceMetaPayload
    lines: List[InvoiceLinePayload] = Field(min_length=1)


class DespatchMetaPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    status: Optional[int] = 0
    local_reference_id: Optional[str] = None
    note: Optional[str] = None
    profile_type: Optional[int] = 0
    type: Optional[int] = 1
    issue_date: str
    prefix: Optional[str] = "EIR"
    currency: Optional[str] = "TRY"
    exchange_rate: Optional[float] = 1


class DeliveryPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    street: Optional[str] = None
    district: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = "Türkiye"
    zip_code: Optional[str] = None


class ShipmentPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    plate_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_surname: Optional[str] = None
    driver_tckn: Optional[str] = None


class DespatchLinePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    product_name: str
    description: Optional[str] = None
    quantity: float = Field(gt=0)
    unit_code: Optional[str] = "C62"
    unit_price: Optional[float] = 0


class EIrsaliyeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    receiver: ReceiverPayload
    despatch: DespatchMetaPayload
    delivery: Optional[DeliveryPayload] = None
    shipment: Optional[ShipmentPayload] = None
    lines: List[DespatchLinePayload] = Field(min_length=1)


class EBelgeCreateResponse(BaseModel):
    id: str  # internal document id
    document_type: str
    provider_id: Optional[str] = None
    document_number: Optional[str] = None
    provider_status: Optional[str] = None
    provider_message: Optional[str] = None
    local_reference_id: Optional[str] = None
    status_internal: str
    trace_id: Optional[str] = None
    raw_provider_body: Optional[Any] = None


class EBelgeStatusResponse(BaseModel):
    provider_id: str
    document_type: str
    success: bool
    provider_status: Optional[str] = None
    provider_message: Optional[str] = None
    raw_provider_body: Optional[Any] = None


class EBelgeDocumentListItem(BaseModel):
    id: str
    document_type: str
    provider_id: Optional[str] = None
    document_number: Optional[str] = None
    receiver_name: Optional[str] = None
    receiver_vkn: Optional[str] = None
    status_internal: str
    provider_status: Optional[str] = None
    created_at: str
    created_by_username: Optional[str] = None


class ProviderConfigStatus(BaseModel):
    api_key_configured: bool
    environment: str  # test | prod
    efatura_base_url: str
    eirsaliye_base_url: str
    has_legacy_fallback: bool
