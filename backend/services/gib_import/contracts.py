from datetime import datetime, timezone
from typing import Optional, List, Literal
from pydantic import BaseModel, Field
import uuid

from .constants import (
    DRAFT_STATUS_PENDING,
    IMPORT_STATUS_PENDING,
    INVOICE_STATUS_IMPORTED,
    PASSWORD_CHANGE_REQUIRED,
)


def _id() -> str:
    return str(uuid.uuid4())


class DraftCustomerRecord(BaseModel):
    id: str = Field(default_factory=_id)
    salesperson_id: str
    tax_no: str
    tc_no: Optional[str] = None
    identity_number: str
    business_name: str
    draft_status: str = DRAFT_STATUS_PENDING
    invoice_count: int = 0
    first_invoice_date: Optional[str] = None
    last_invoice_date: Optional[str] = None
    total_amount: float = 0.0
    source_invoice_ids: List[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CustomerRecord(BaseModel):
    id: str = Field(default_factory=_id)
    salesperson_id: str
    draft_customer_id: Optional[str] = None
    business_name: str
    tax_no: str
    tc_no: Optional[str] = None
    identity_number: str
    customer_type: Optional[str] = None
    risk_limit: float = 0.0
    balance: float = 0.0
    phone: str = ''
    address: str = ''
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CustomerUserRecord(BaseModel):
    id: str = Field(default_factory=_id)
    customer_id: str
    username: str
    password_hash: str
    must_change_password: bool = PASSWORD_CHANGE_REQUIRED
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InvoiceRecord(BaseModel):
    id: str = Field(default_factory=_id)
    salesperson_id: str
    import_job_id: Optional[str] = None
    customer_id: Optional[str] = None
    draft_customer_id: Optional[str] = None
    ettn: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    business_name: str
    tax_no: str
    tc_no: Optional[str] = None
    identity_number: str
    currency: str = 'TRY'
    grand_total: float = 0.0
    raw_payload: dict = Field(default_factory=dict)
    status: str = INVOICE_STATUS_IMPORTED
    is_cancelled: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InvoiceLineRecord(BaseModel):
    id: str = Field(default_factory=_id)
    invoice_id: str
    product_id: Optional[str] = None
    line_no: int
    product_code: Optional[str] = None
    product_name: str
    normalized_name: str
    quantity: float = 0.0
    unit_price: float = 0.0
    line_total: float = 0.0
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductRecord(BaseModel):
    id: str = Field(default_factory=_id)
    product_code: Optional[str] = None
    name: str
    normalized_name: str
    unit: Optional[str] = None
    shelf_life_days: Optional[int] = None
    is_active: bool = True
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ProductAliasRecord(BaseModel):
    id: str = Field(default_factory=_id)
    product_id: str
    alias: str
    normalized_alias: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CustomerProductConsumptionRecord(BaseModel):
    id: str = Field(default_factory=_id)
    customer_id: str
    product_id: str
    last_invoice_date: Optional[str] = None
    last_quantity: Optional[float] = None
    daily_consumption: Optional[float] = None
    average_order_quantity: Optional[float] = None
    estimated_days_to_depletion: Optional[float] = None
    rate_mt_weighted: Optional[float] = None
    interval_count: int = 0
    skipped_interval_count: int = 0
    confidence_score: float = 0.0
    trend: str = 'stable'
    invoice_count: int = 0
    normalization_source: Optional[str] = None
    last_calculated_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class CustomerProductDailyConsumptionRecord(BaseModel):
    id: str = Field(default_factory=_id)
    customer_id: str
    product_id: str
    date: str
    daily_rate: float
    source_start_invoice_id: Optional[str] = None
    source_end_invoice_id: Optional[str] = None
    day_diff: int
    method: str = 'interval_spread'
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class GibImportJobRecord(BaseModel):
    id: str = Field(default_factory=_id)
    salesperson_id: str
    status: str = IMPORT_STATUS_PENDING
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    invoice_count: int = 0
    error_message: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DraftCustomerApprovePayload(BaseModel):
    customer_type: str
    risk_limit: float
    balance: float
    phone: str
    address: str


class ImportStartPayload(BaseModel):
    source: Literal['gib_portal'] = 'gib_portal'


class CustomerLoginPayload(BaseModel):
    username: str
    password: str


class CustomerChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str


class LiveGibConnectPayload(BaseModel):
    username: str
    password: str
    mode: Literal['live'] = 'live'


class LiveGibImportPayload(BaseModel):
    date_from: str
    date_to: str
