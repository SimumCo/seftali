from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from datetime import date


class EInvoiceStatus(str, Enum):
    DRAFT = 'draft'
    QUEUED = 'queued'
    PROCESSING = 'processing'
    SENT = 'sent'
    FAILED = 'failed'


class EInvoiceReceiver(BaseModel):
    vkn_tckn: str
    alias: str
    title: str

    @field_validator('vkn_tckn')
    @classmethod
    def validate_vkn_tckn(cls, value: str):
        digits = ''.join(ch for ch in str(value) if ch.isdigit())
        if len(digits) not in {10, 11}:
            raise ValueError('receiver.vkn_tckn must be 10 or 11 digits')
        return digits


class EInvoiceLine(BaseModel):
    name: str
    quantity: Decimal
    unit_code: str = 'NIU'
    unit_price: Decimal
    vat_rate: Decimal

    @field_validator('quantity', 'unit_price')
    @classmethod
    def validate_positive_decimal(cls, value: Decimal):
        if value <= 0:
            raise ValueError('quantity and unit_price must be positive')
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @field_validator('vat_rate')
    @classmethod
    def validate_vat_rate(cls, value: Decimal):
        if value < 0:
            raise ValueError('vat_rate must be non-negative')
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


class EInvoiceCreateRequest(BaseModel):
    local_reference_id: str
    issue_date: date
    receiver: EInvoiceReceiver
    lines: List[EInvoiceLine] = Field(min_length=1)
    customer_id: Optional[str] = None
    scenario: Optional[str] = 'TEMELFATURA'


class EInvoiceCreateResult(BaseModel):
    invoice_id: str
    local_reference_id: str
    status: EInvoiceStatus
    provider_name: str
    provider_invoice_id: Optional[str] = None
    invoice_number: Optional[str] = None
    provider_status_code: Optional[str] = None
    provider_status_message: Optional[str] = None


class EInvoiceStatusResult(BaseModel):
    invoice_id: str
    status: EInvoiceStatus
    provider_invoice_id: Optional[str] = None
    provider_status_code: Optional[str] = None
    provider_status_message: Optional[str] = None
