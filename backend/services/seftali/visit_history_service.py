"""
Plasiyer Rota Ziyaret Geçmişi & Akıllı Sıralama Servisi
- Yalnızca 'visited' / 'visited_without_invoice' sonuçları kaydedilir.
- Önerilen sıra, plasiyer + route_day bazında izole hesaplanır.
- Üç katmanlı mantık: ortalama visit_order -> ortalama visited_at saati -> mevcut visit_order fallback.
"""
from typing import Dict, List, Optional
from datetime import datetime, timezone

from config.database import db
from services.seftali.core import (
    COL_ROUTE_VISIT_HISTORY,
    gen_id,
    now_utc,
    to_iso,
)

VALID_PERSISTED_RESULTS = {"visited", "visited_without_invoice"}


async def record_visit(
    *,
    salesperson_id: str,
    customer_id: str,
    route_day: str,
    visit_result: str,
    visit_order: Optional[int] = None,
    invoice_created: bool = False,
    visited_at: Optional[str] = None,
) -> Optional[dict]:
    """Bir rut aksiyonunu geçmiş koleksiyonuna kaydeder. not_visited kaydedilmez."""
    if visit_result not in VALID_PERSISTED_RESULTS:
        return None

    doc = {
        "id": gen_id(),
        "salesperson_id": salesperson_id,
        "customer_id": customer_id,
        "route_day": (route_day or "").upper(),
        "visit_order": int(visit_order) if visit_order is not None else None,
        "visited_at": visited_at or to_iso(now_utc()),
        "visit_result": visit_result,
        "invoice_created": bool(invoice_created),
        "created_at": to_iso(now_utc()),
    }
    await db[COL_ROUTE_VISIT_HISTORY].insert_one(doc)
    return doc


async def get_history(
    salesperson_id: str,
    route_day: str,
    customer_ids: Optional[List[str]] = None,
) -> List[dict]:
    """Plasiyer + gün bazlı kayıtları getirir (diğer günler/plasiyerler dahil edilmez)."""
    query = {
        "salesperson_id": salesperson_id,
        "route_day": (route_day or "").upper(),
        "visit_result": {"$in": list(VALID_PERSISTED_RESULTS)},
    }
    if customer_ids:
        query["customer_id"] = {"$in": list(customer_ids)}

    cursor = db[COL_ROUTE_VISIT_HISTORY].find(query, {"_id": 0})
    return await cursor.to_list(length=10000)


def _minutes_of_day(iso_str: str) -> Optional[int]:
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        return dt.hour * 60 + dt.minute
    except Exception:
        return None


async def compute_suggested_orders(
    salesperson_id: str,
    route_day: str,
    customers: List[dict],
) -> Dict[str, int]:
    """
    Müşteri başına önerilen sıra (1..N) hesaplar.
    Sıralama anahtarı (öncelik sırasıyla):
      1. Aynı (plasiyer, gün) için ortalama visit_order (varsa)
      2. Yoksa ortalama visited_at saati (dakika)
      3. Yoksa mevcut manuel visit_order
    """
    if not customers:
        return {}

    customer_ids = [c.get("id") for c in customers if c.get("id")]
    history = await get_history(salesperson_id, route_day, customer_ids)

    by_customer: Dict[str, List[dict]] = {}
    for h in history:
        cid = h.get("customer_id")
        if cid:
            by_customer.setdefault(cid, []).append(h)

    def _key_for(c: dict):
        cid = c.get("id")
        records = by_customer.get(cid, [])

        order_vals = [
            r.get("visit_order") for r in records
            if isinstance(r.get("visit_order"), (int, float))
        ]
        if order_vals:
            return (0, sum(order_vals) / len(order_vals))

        minute_vals = [
            _minutes_of_day(r.get("visited_at")) for r in records
        ]
        minute_vals = [m for m in minute_vals if m is not None]
        if minute_vals:
            return (1, sum(minute_vals) / len(minute_vals))

        fallback = c.get("visit_order") or 0
        return (2, float(fallback))

    sorted_customers = sorted(customers, key=_key_for)
    return {c.get("id"): idx + 1 for idx, c in enumerate(sorted_customers) if c.get("id")}
