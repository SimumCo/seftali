from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from models.user import UserRole
from utils.auth import require_role
from services.seftali.core import std_resp
from services.seftali.smart_order_service import SmartOrderService

router = APIRouter(prefix="/sales", tags=["Seftali-Sales-SmartOrders"])

SALES_ROLES = [UserRole.SALES_REP, UserRole.SALES_AGENT]


class WarehouseSubmitBody(BaseModel):
    note: str = ""


@router.get("/warehouse-draft")
@router.get("/smart-orders")
async def get_warehouse_draft(
    route_day: Optional[str] = None,
    current_user=Depends(require_role(SALES_ROLES))
):
    data = await SmartOrderService.get_smart_orders(
        salesperson_id=current_user.id,
        route_day=route_day,
    )
    return std_resp(True, data)


@router.get("/smart-draft-v2")
async def get_smart_draft_v2(current_user=Depends(require_role(SALES_ROLES))):
    data = await SmartOrderService.get_smart_draft_v2(current_user.id)
    return std_resp(True, data)


@router.post("/warehouse-draft/submit")
@router.post("/smart-orders/submit")
async def submit_warehouse_draft(body: WarehouseSubmitBody, current_user=Depends(require_role(SALES_ROLES))):
    """
    Depo sipariş taslağını depoya gönderir.
    Saat 17:00 kontrolü frontend'de yapılır.
    """
    warehouse_order = await SmartOrderService.submit_smart_orders(
        salesperson_id=current_user.id,
        note=body.note,
    )
    return std_resp(True, warehouse_order, "Depo siparisi basariyla gonderildi")


@router.get("/plasiyer/order-calculation")
async def calculate_plasiyer_order(
    route_day: Optional[str] = None,
    current_user=Depends(require_role(SALES_ROLES))
):
    """
    Plasiyerin yarınki (veya belirtilen gün) rota için ihtiyaç listesini hesapla.

    - Sipariş atan müşterilerin siparişleri
    - Sipariş atmayan müşterilerin draft'ları
    - Toplam ihtiyaç - Plasiyer stoğu = Sipariş listesi
    """
    result = await SmartOrderService.calculate_plasiyer_order(
        salesperson_id=current_user.id,
        route_day=route_day,
    )
    return std_resp(True, result)


@router.get("/route-order/{route_day}")
async def get_route_order(route_day: str, current_user=Depends(require_role(SALES_ROLES))):
    """
    Plasiyerin belirli bir rota günü için sipariş ihtiyacını hesapla.

    Hesaplama adımları:
    1. O gün rotasındaki müşterileri bul
    2. Sipariş atanların siparişlerini al
    3. Sipariş atmayanların draft'larını al
    4. Toplam ihtiyaçtan plasiyer stoğunu düş
    5. Koli yuvarlaması uygula
    """
    try:
        result = await SmartOrderService.get_route_order(
            salesperson_id=current_user.id,
            route_day=route_day,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return std_resp(True, result)


@router.get("/route-order")
async def get_route_order_tomorrow(current_user=Depends(require_role(SALES_ROLES))):
    """Yarınki rota için sipariş ihtiyacını hesapla."""
    result = await SmartOrderService.get_route_order_tomorrow(current_user.id)
    return std_resp(True, result)
