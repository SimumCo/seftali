from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from models.user import UserRole
from utils.auth import require_role
from services.seftali.core import std_resp
from services.seftali.order_service import OrderService

router = APIRouter(prefix="/sales", tags=["Seftali-Sales-Orders"])

SALES_ROLES = [UserRole.SALES_REP, UserRole.SALES_AGENT]


class OrderActionBody(BaseModel):
    note: str = ""


@router.get("/orders")
async def list_orders(
    status: Optional[str] = None,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    current_user=Depends(require_role(SALES_ROLES)),
):
    items = await OrderService.list_orders(
        status=status,
        from_date=from_date,
        to_date=to_date,
    )
    return std_resp(True, items)


@router.post("/orders/{order_id}/approve")
async def approve_order(order_id: str, current_user=Depends(require_role(SALES_ROLES))):
    result = await OrderService.approve_order(order_id)
    if not result:
        raise HTTPException(404, "Siparis bulunamadi")
    return std_resp(True, result, "Siparis onaylandi")


@router.post("/orders/{order_id}/request-edit")
async def request_edit(order_id: str, body: OrderActionBody, current_user=Depends(require_role(SALES_ROLES))):
    try:
        result = await OrderService.request_edit(order_id, body.note)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    if not result:
        raise HTTPException(404, "Siparis bulunamadi")
    return std_resp(True, result, "Duzenleme istegi gonderildi")
