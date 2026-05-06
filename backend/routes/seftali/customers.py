from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query

from models.user import UserRole
from utils.auth import require_role
from services.seftali.core import std_resp
from services.seftali.customer_service import CustomerService
from services.gib_import.consumption_service import (
    CustomerConsumptionService,
    ConsumptionCalculationError,
)

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


# ============================================================
# YoY (Year-over-Year) Karşılaştırma & Trend Analizi
# ============================================================

@router.get("/customers/{customer_id}/consumption/yoy")
async def get_customer_yoy_overview(
    customer_id: str,
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    current_user=Depends(require_role(SALES_ROLES)),
):
    """
    Müşterinin tüm ürünleri için bu ay vs geçen yılın aynı ayı karşılaştırması.
    Plasiyere mevsimsel trend sinyali verir (örn: 'Mart yaklaşıyor, ayran %85 artmıştı').
    """
    today = datetime.utcnow()
    target_year = year or today.year
    target_month = month or today.month
    service = CustomerConsumptionService()
    try:
        result = await service.yoy_overview(customer_id, target_year, target_month)
    except ConsumptionCalculationError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return std_resp(True, {
        'year': target_year,
        'month': target_month,
        'previous_year': target_year - 1,
        'items': result,
    })


@router.get("/customers/{customer_id}/consumption/yoy/{product_id}")
async def get_customer_yoy_product(
    customer_id: str,
    product_id: str,
    year: int | None = Query(None, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    current_user=Depends(require_role(SALES_ROLES)),
):
    """Tek bir ürün için aylık YoY karşılaştırması."""
    today = datetime.utcnow()
    target_year = year or today.year
    target_month = month or today.month
    service = CustomerConsumptionService()
    try:
        result = await service.compare_yoy(customer_id, product_id, target_year, target_month)
    except ConsumptionCalculationError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return std_resp(True, result)


@router.get("/customers/{customer_id}/consumption/trend/{product_id}")
async def get_customer_trend(
    customer_id: str,
    product_id: str,
    year: int | None = Query(None, ge=2000, le=2100),
    current_user=Depends(require_role(SALES_ROLES)),
):
    """Bir ürünün yıllık (12 aylık) trend ve mevsimsellik analizi."""
    target_year = year or datetime.utcnow().year
    service = CustomerConsumptionService()
    try:
        result = await service.analyze_yearly_trend(customer_id, product_id, target_year)
    except ConsumptionCalculationError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return std_resp(True, result)
