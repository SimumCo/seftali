"""
Rota Haritası & Optimizasyon Endpoint'leri
GET  /seftali/sales/route-map/{route_day}      - Günlük rota müşterileri + optimize edilmiş sıra
POST /seftali/sales/route-map/optimize         - Rota sırasını yeniden optimize et
POST /seftali/sales/route-map/visit            - Plasiyerin rut aksiyonunu kaydet
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from models.user import UserRole
from utils.auth import require_role
from config.database import db
from services.seftali.core import std_resp, COL_CUSTOMERS, COL_SETTINGS, DAY_MAP
from services.seftali.route_optimizer import nearest_neighbor_optimize, calculate_total_distance_km
from services.seftali.visit_history_service import (
    compute_suggested_orders,
    record_visit,
    VALID_PERSISTED_RESULTS,
)

router = APIRouter(prefix="/sales", tags=["Seftali-RouteMap"])

SALES_ROLES = [UserRole.SALES_REP, UserRole.SALES_AGENT]

DAY_CODE_MAP = {v: k for k, v in {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3,
    "FRI": 4, "SAT": 5, "SUN": 6
}.items()}


class OptimizeBody(BaseModel):
    route_day: str
    start_lat: Optional[float] = None
    start_lng: Optional[float] = None


class VisitBody(BaseModel):
    customer_id: str
    route_day: str
    visit_result: str
    visit_order: Optional[int] = None
    invoice_created: bool = False
    visited_at: Optional[str] = None


async def _get_smart_ordering_enabled() -> bool:
    """sf_system_settings içinden smart_ordering_enabled bayrağını okur (default True)."""
    settings = await db[COL_SETTINGS].find_one({"type": "order_settings"}, {"_id": 0})
    if not settings:
        return True
    val = settings.get("smart_ordering_enabled")
    return True if val is None else bool(val)


async def _fetch_route_customers(route_day: str, salesperson_id: str) -> list:
    """Verilen gün için plasiyerin rota müşterilerini getirir."""
    cursor = db[COL_CUSTOMERS].find(
        {"is_active": True, "route_plan.days": route_day, "user_id": salesperson_id},
        {"_id": 0}
    )
    customers = await cursor.to_list(length=500)

    result = []
    for c in customers:
        loc = c.get("location") or {}
        lat = loc.get("lat") or loc.get("latitude")
        lng = loc.get("lng") or loc.get("longitude") or loc.get("lon")

        result.append({
            "id": c.get("id", ""),
            "name": c.get("name", ""),
            "code": c.get("code", ""),
            "phone": c.get("phone", ""),
            "address": c.get("address", "") or loc.get("address", ""),
            "district": c.get("district", "") or loc.get("district", ""),
            "location": {
                "lat": float(lat) if lat is not None else None,
                "lng": float(lng) if lng is not None else None,
                "address": loc.get("address", ""),
            },
            "route_plan": c.get("route_plan", {}),
            "order_status": c.get("last_order_status", "no_order"),
            "visit_order": c.get("route_plan", {}).get("sequence", 0) or 0,
            "status": "pending",
        })

    return result


def _attach_suggested(customers: list, suggested_map: dict) -> None:
    """Her müşteriye suggested_visit_order alanını yazar (manuel visit_order'ı bozmaz)."""
    for c in customers:
        cid = c.get("id")
        c["suggested_visit_order"] = suggested_map.get(cid) or c.get("visit_order") or 0


@router.get("/route-map/{route_day}")
async def get_route_map(
    route_day: str,
    optimize: bool = Query(True, description="Nearest-neighbor optimizasyonu uygula"),
    start_lat: Optional[float] = Query(None),
    start_lng: Optional[float] = Query(None),
    current_user=Depends(require_role(SALES_ROLES)),
):
    """
    Plasiyer'in verilen gün için rota müşterilerini harita verileriyle döndürür.
    optimize=true ise nearest-neighbor algoritmasıyla sıra optimize edilir.
    Yanıtta her müşteri için manuel visit_order ile birlikte
    geçmişe dayalı suggested_visit_order alanı da yer alır.
    """
    route_day = route_day.upper()
    customers = await _fetch_route_customers(route_day, current_user.id)

    if optimize and customers:
        customers = nearest_neighbor_optimize(customers, start_lat, start_lng)
    else:
        for i, c in enumerate(customers):
            if not c.get("visit_order"):
                c["visit_order"] = i + 1

    suggested_map = await compute_suggested_orders(current_user.id, route_day, customers)
    _attach_suggested(customers, suggested_map)

    smart_enabled = await _get_smart_ordering_enabled()

    mapped_count = sum(
        1 for c in customers
        if c.get("location", {}).get("lat") is not None
    )

    total_distance = calculate_total_distance_km(customers) if optimize else None

    return std_resp(True, {
        "route_day": route_day,
        "customers": customers,
        "total": len(customers),
        "mapped_count": mapped_count,
        "optimized": optimize,
        "total_distance_km": total_distance,
        "smart_ordering_enabled": smart_enabled,
    })


@router.post("/route-map/optimize")
async def optimize_route(
    body: OptimizeBody,
    current_user=Depends(require_role(SALES_ROLES)),
):
    """Mevcut rota müşterilerini verilen başlangıç noktasına göre yeniden optimize eder."""
    route_day = body.route_day.upper()
    customers = await _fetch_route_customers(route_day, current_user.id)

    optimized = nearest_neighbor_optimize(customers, body.start_lat, body.start_lng)

    suggested_map = await compute_suggested_orders(current_user.id, route_day, optimized)
    _attach_suggested(optimized, suggested_map)

    total_distance = calculate_total_distance_km(optimized)

    return std_resp(True, {
        "route_day": route_day,
        "customers": optimized,
        "total": len(optimized),
        "total_distance_km": total_distance,
        "optimized": True,
        "smart_ordering_enabled": await _get_smart_ordering_enabled(),
    }, "Rota optimize edildi")


@router.post("/route-map/visit")
async def record_route_visit(
    body: VisitBody,
    current_user=Depends(require_role(SALES_ROLES)),
):
    """Plasiyerin rut aksiyonunu kaydeder. not_visited kayıtları sessizce yok sayılır."""
    if body.visit_result not in VALID_PERSISTED_RESULTS and body.visit_result != "not_visited":
        return std_resp(False, message="Geçersiz visit_result")

    saved = await record_visit(
        salesperson_id=current_user.id,
        customer_id=body.customer_id,
        route_day=body.route_day,
        visit_result=body.visit_result,
        visit_order=body.visit_order,
        invoice_created=body.invoice_created,
        visited_at=body.visited_at,
    )
    return std_resp(True, {"recorded": saved is not None})
