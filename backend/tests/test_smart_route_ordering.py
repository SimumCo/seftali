"""
Akıllı rota sıralaması — visit_history_service için birim testleri.
Adaptör PostgreSQL'e bağlandığı için temiz başlangıç adına test verisi
benzersiz salesperson_id'ler kullanılarak izole edilir.
"""
import asyncio
import uuid
import pytest

from services.seftali.visit_history_service import (
    record_visit,
    get_history,
    compute_suggested_orders,
)


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_history_isolated_per_day():
    sp = _uid("sp")
    c1 = _uid("c1")
    c2 = _uid("c2")

    await record_visit(salesperson_id=sp, customer_id=c1, route_day="MON",
                       visit_result="visited", visit_order=1)
    await record_visit(salesperson_id=sp, customer_id=c2, route_day="TUE",
                       visit_result="visited", visit_order=1)

    mon = await get_history(sp, "MON")
    tue = await get_history(sp, "TUE")
    assert {h["customer_id"] for h in mon} == {c1}
    assert {h["customer_id"] for h in tue} == {c2}


@pytest.mark.asyncio
async def test_history_isolated_per_salesperson():
    sp_a, sp_b = _uid("spa"), _uid("spb")
    c1 = _uid("c")

    await record_visit(salesperson_id=sp_a, customer_id=c1, route_day="WED",
                       visit_result="visited", visit_order=2)

    a = await get_history(sp_a, "WED")
    b = await get_history(sp_b, "WED")
    assert len(a) == 1
    assert b == []


@pytest.mark.asyncio
async def test_not_visited_not_persisted():
    sp = _uid("sp")
    c1 = _uid("c")
    saved = await record_visit(salesperson_id=sp, customer_id=c1, route_day="THU",
                               visit_result="not_visited", visit_order=1)
    assert saved is None
    assert await get_history(sp, "THU") == []


@pytest.mark.asyncio
async def test_suggested_orders_average_visit_order():
    sp = _uid("sp")
    c1, c2, c3 = _uid("a"), _uid("b"),  _uid("c")
    # c2 her zaman 1, c1 her zaman 2, c3 her zaman 3 -> beklenen sıra: c2, c1, c3
    for _ in range(2):
        await record_visit(salesperson_id=sp, customer_id=c2, route_day="FRI",
                           visit_result="visited", visit_order=1)
        await record_visit(salesperson_id=sp, customer_id=c1, route_day="FRI",
                           visit_result="visited", visit_order=2)
        await record_visit(salesperson_id=sp, customer_id=c3, route_day="FRI",
                           visit_result="visited_without_invoice", visit_order=3)

    customers = [
        {"id": c1, "visit_order": 99},
        {"id": c2, "visit_order": 99},
        {"id": c3, "visit_order": 99},
    ]
    sug = await compute_suggested_orders(sp, "FRI", customers)
    assert sug[c2] == 1
    assert sug[c1] == 2
    assert sug[c3] == 3


@pytest.mark.asyncio
async def test_suggested_orders_falls_back_to_time():
    sp = _uid("sp")
    c1, c2 = _uid("a"), _uid("b")
    # visit_order None — sadece saat sinyali. c1 sabah 08:00, c2 öğlen 14:00.
    await record_visit(salesperson_id=sp, customer_id=c1, route_day="SAT",
                       visit_result="visited", visit_order=None,
                       visited_at="2025-01-04T08:00:00+00:00")
    await record_visit(salesperson_id=sp, customer_id=c2, route_day="SAT",
                       visit_result="visited", visit_order=None,
                       visited_at="2025-01-04T14:00:00+00:00")

    customers = [{"id": c2, "visit_order": 1}, {"id": c1, "visit_order": 2}]
    sug = await compute_suggested_orders(sp, "SAT", customers)
    assert sug[c1] == 1
    assert sug[c2] == 2


@pytest.mark.asyncio
async def test_suggested_orders_fallback_when_no_history():
    sp = _uid("sp")
    c1, c2 = _uid("a"), _uid("b")
    customers = [{"id": c1, "visit_order": 5}, {"id": c2, "visit_order": 2}]
    sug = await compute_suggested_orders(sp, "SUN", customers)
    # Geçmiş yok -> mevcut visit_order'a göre sıralanır
    assert sug[c2] == 1
    assert sug[c1] == 2
