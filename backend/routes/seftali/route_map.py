"""
Rota Haritası & Optimizasyon Endpoint'leri
GET  /seftali/sales/route-map/{route_day}      - Günlük rota müşterileri + optimize edilmiş sıra
POST /seftali/sales/route-map/optimize         - Rota sırasını yeniden optimize et
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from models.user import UserRole
from utils.auth import require_role
from config.database import db
from services.seftali.core import std_resp, COL_CUSTOMERS, DAY_MAP
from services.seftali.route_optimizer import nearest_neighbor_optimize, calculate_total_distance_km

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


async def _fetch_route_customers(route_day: str, salesperson_id: str) -> list:
    """Verilen gün için plasiyerin rota müşterilerini getirir."""
    cursor = db[COL_CUSTOMERS].find(
        {"is_active": True, "route_plan.days": route_day},
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
    """
    route_day = route_day.upper()
    customers = await _fetch_route_customers(route_day, current_user.id)

    if optimize and customers:
        customers = nearest_neighbor_optimize(customers, start_lat, start_lng)
    else:
        for i, c in enumerate(customers):
            if not c.get("visit_order"):
                c["visit_order"] = i + 1

    # Koordinatı olan müşteri sayısı
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
    total_distance = calculate_total_distance_km(optimized)

    return std_resp(True, {
        "route_day": route_day,
        "customers": optimized,
        "total": len(optimized),
        "total_distance_km": total_distance,
        "optimized": True,
    }, "Rota optimize edildi")
