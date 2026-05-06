"""
Plasiyer rota müşterileri izolasyonu testi.
_fetch_route_customers yalnızca current_user.id'ye atanmış müşterileri döndürmeli.
"""
import uuid
import pytest

from config.database import db
from services.seftali.core import COL_CUSTOMERS
from routes.seftali.route_map import _fetch_route_customers


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def _insert_customer(cid: str, user_id: str, day: str) -> None:
    await db[COL_CUSTOMERS].insert_one({
        "id": cid,
        "name": cid,
        "code": cid,
        "is_active": True,
        "user_id": user_id,
        "route_plan": {"days": [day], "sequence": 1},
        "location": {"lat": 41.0, "lng": 29.0},
    })


@pytest.mark.asyncio
async def test_route_map_isolated_per_salesperson():
    sp_a, sp_b = _uid("spa"), _uid("spb")
    day = "MON"
    c_a1, c_a2, c_b = _uid("ca1"), _uid("ca2"), _uid("cb")
    try:
        await _insert_customer(c_a1, sp_a, day)
        await _insert_customer(c_a2, sp_a, day)
        await _insert_customer(c_b, sp_b, day)

        a = await _fetch_route_customers(day, sp_a)
        b = await _fetch_route_customers(day, sp_b)

        a_ids = {c["id"] for c in a}
        b_ids = {c["id"] for c in b}

        assert c_a1 in a_ids and c_a2 in a_ids
        assert c_b not in a_ids
        assert b_ids == {c_b}
        assert a_ids.isdisjoint(b_ids)
    finally:
        for cid in (c_a1, c_a2, c_b):
            await db[COL_CUSTOMERS].delete_one({"id": cid})
