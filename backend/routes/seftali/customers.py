from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from models.user import UserRole
from utils.auth import require_role
from services.seftali.core import std_resp
from services.seftali.customer_service import CustomerService

router = APIRouter(prefix="/sales", tags=["Seftali-Sales-Customers"])

SALES_ROLES = [UserRole.SALES_REP, UserRole.SALES_AGENT]


@router.get("/customers")
async def list_customers(current_user=Depends(require_role(SALES_ROLES))):
    items = await CustomerService.list_customers()
    return std_resp(True, items)


@router.get("/customers/{customer_id}/consumption")
async def get_customer_consumption(customer_id: str, current_user=Depends(require_role(SALES_ROLES))):
    """
    Plasiyer'in müşteri tüketim istatistiklerini görmesi için endpoint.
    Ürün bazında günlük ortalama tüketim ve toplam tüketim.
    """
    result = await CustomerService.get_customer_consumption(customer_id)
    if not result:
        raise HTTPException(404, "Müşteri bulunamadı")
    return std_resp(True, result)


@router.get("/customers/summary")
async def get_customers_summary(current_user=Depends(require_role(SALES_ROLES))):
    """
    Plasiyer müşteri kartları için özet veriler:
    - Vadesi geçmiş faturalar
    - Bekleyen siparişler
    - Son teslimat tarihi
    - Toplam sipariş sayısı
    """
    customer_summaries = await CustomerService.get_customers_summary()
    return std_resp(True, customer_summaries)
