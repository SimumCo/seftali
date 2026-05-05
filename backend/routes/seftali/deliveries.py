from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from models.user import UserRole
from utils.auth import require_role
from services.seftali.core import std_resp
from services.seftali.delivery_service import DeliveryService

router = APIRouter(prefix="/sales", tags=["Seftali-Sales-Deliveries"])

SALES_ROLES = [UserRole.SALES_REP, UserRole.SALES_AGENT]


class DeliveryItem(BaseModel):
    product_id: str
    qty: float

    @field_validator("qty")
    @classmethod
    def qty_pos(cls, value):
        if value <= 0:
            raise ValueError("qty sifirdan buyuk olmali")
        return value


class CreateDeliveryBody(BaseModel):
    customer_id: str
    delivery_type: str = "route"
    delivered_at: Optional[str] = None
    invoice_no: Optional[str] = None
    items: List[DeliveryItem]

    @field_validator("items")
    @classmethod
    def validate_items(cls, value):
        if not value:
            raise ValueError("En az bir urun gerekli")
        product_ids = [item.product_id for item in value]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Tekrarlayan urun_id")
        return value

    @field_validator("delivery_type")
    @classmethod
    def check_type(cls, value):
        if value not in ("route", "off_route"):
            raise ValueError("delivery_type: route veya off_route olmali")
        return value


@router.post("/deliveries")
async def create_delivery(body: CreateDeliveryBody, current_user=Depends(require_role(SALES_ROLES))):
    delivery, message = await DeliveryService.create_delivery(
        customer_id=body.customer_id,
        delivery_type=body.delivery_type,
        delivered_at=body.delivered_at,
        invoice_no=body.invoice_no,
        items=[{"product_id": item.product_id, "qty": item.qty} for item in body.items],
        salesperson_id=current_user.id,
    )
    if not delivery:
        raise HTTPException(404, message)
    return std_resp(True, delivery, message)


@router.get("/deliveries")
async def list_deliveries(
    status: Optional[str] = None,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    current_user=Depends(require_role(SALES_ROLES)),
):
    items = await DeliveryService.list_deliveries(
        status=status,
        from_date=from_date,
        to_date=to_date,
    )
    return std_resp(True, items)
