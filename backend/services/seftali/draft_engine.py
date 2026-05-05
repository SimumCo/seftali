"""
ŞEFTALİ - Draft Engine 2.0
Gelişmiş tahmini ihtiyaç hesaplama motoru

Kullanılan Parametreler:
- prev_delivery_qty: Önceki teslimat miktarı
- prev_delivery_date: Önceki teslimat tarihi
- curr_delivery_date: Son teslimat tarihi
- interval_rates: Son N interval'in günlük tüketim oranları
- weekly_multiplier: Haftalık mevsimsellik çarpanı
- today_date: Bugünün tarihi
- next_route_date: Sonraki rut tarihi
- supply_days: Ardışık rutlar arası gün sayısı

Hesaplama Formülü:
    daily_rate = prev_qty / days_between (her interval için)
    rate_mt = SMA(son 8 interval rate)
    rate_used = rate_mt × weekly_multiplier
    need_qty = rate_used × supply_days
"""

from typing import Dict, List, Any, Optional
from datetime import timedelta
from config.database import db

from .core import (
    now_utc, to_iso, parse_date, get_route_info,
    SMA_WINDOW, EPSILON, WEEKDAY_NAMES,
    COL_CUSTOMERS, COL_PRODUCTS, COL_DELIVERIES,
    COL_SYSTEM_DRAFTS, COL_DE_STATE, COL_DE_MULTIPLIERS
)
from services.gib_import.constants import COLL_CUSTOMER_PRODUCT_CONSUMPTIONS


class DraftEngine:
    """
    Draft Engine 2.0 - Ana hesaplama sınıfı
    
    Bu sınıf müşteri bazında tahmini ihtiyaç hesaplaması yapar.
    SMA (Simple Moving Average) tabanlı, interval-based bir algoritma kullanır.
    """
    
    # =========================================================================
    # PUBLIC METHODS
    # =========================================================================
    
    @classmethod
    async def calculate(cls, customer_id: str) -> Optional[Dict[str, Any]]:
        """
        Müşteri için tahmini ihtiyaç hesapla.
        
        Args:
            customer_id: Müşteri ID'si
            
        Returns:
            Draft objesi veya None
        """
        now = now_utc()
        today = now.date()
        
        # Müşteri bilgisi
        customer = await db[COL_CUSTOMERS].find_one(
            {"id": customer_id}, {"_id": 0}
        )
        if not customer:
            return None
        
        route_days = customer.get("route_plan", {}).get("days", [])
        route_info = get_route_info(route_days)
        
        analytics_customer_id = customer.get('customer_id') or customer_id

        # Ürün durumlarını al
        states = await cls._get_product_states(customer_id)
        state_map = {state['product_id']: state for state in states}

        # Yeni aggregate consumption verisi (primary source)
        consumptions = await cls._get_customer_product_consumptions(analytics_customer_id)

        product_ids = sorted(set(state_map.keys()) | set(consumptions.keys()))
        if not product_ids:
            return cls._empty_draft(customer_id, customer, route_info, now)

        # Ürün bilgileri
        products = await cls._get_products(product_ids)
        
        # Haftalık çarpanlar
        multipliers = await cls._get_weekly_multipliers(today, customer, product_ids)
        
        # Her ürün için hesapla
        items = []
        excluded_items = []
        for product_id in product_ids:
            state = state_map.get(product_id)
            aggregate = consumptions.get(product_id)
            item = cls._calculate_item(product_id, state, aggregate, products, multipliers, route_info, today)
            if item.get("abandoned"):
                excluded_items.append(item)
            else:
                items.append(item)
        
        # Sırala (yüksek ihtiyaçtan düşüğe)
        items.sort(key=lambda x: (x.get("need_qty") or 0), reverse=True)
        for i, item in enumerate(items):
            item["priority_rank"] = i + 1
        
        # Next route date
        next_route_date = (today + timedelta(days=route_info["days_to_next_route"])).isoformat()
        next_route_weekday = WEEKDAY_NAMES[route_info["next_route_weekday"]] if route_info["next_route_weekday"] is not None else None
        
        return {
            "customer_id": customer_id,
            "customer_name": customer.get("name", ""),
            "route_days": route_days,
            "route_info": {
                "days_to_next_route": route_info["days_to_next_route"],
                "supply_days": route_info["supply_days"],
                "next_route_date": next_route_date,
                "next_route_weekday": next_route_weekday
            },
            "calculation_params": {
                "today_date": today.isoformat(),
                "sma_window": SMA_WINDOW,
                "formula": "need_qty = rate_base × weekly_multiplier × days_to_next_route",
                "formula_version": "v2-dual-read"
            },
            "items": items,
            "excluded_items": excluded_items,
            "summary": {
                "total_products": len(items),
                "products_abandoned": len(excluded_items),
                "total_need_qty": sum(i.get("need_qty") or 0 for i in items),
                "products_with_data": len([i for i in items if i.get("rate_mt_weighted") or i.get("rate_mt")]),
                "products_low_data": len([i for i in items if i.get("flags", {}).get("low_data")])
            },
            "generated_at": to_iso(now),
            "generated_from": "draft_engine_v2"
        }
    
    @classmethod
    async def save(cls, customer_id: str, source: str = "system") -> Optional[dict]:
        """
        Hesaplanan draft'ı veritabanına kaydet.
        
        Args:
            customer_id: Müşteri ID'si
            source: Kaynak (system, delivery_event, route_change, vb.)
            
        Returns:
            Kaydedilen draft veya None
        """
        draft = await cls.calculate(customer_id)
        if not draft:
            return None
        
        now = now_utc()
        
        # Legacy format için dönüştür
        legacy_items = []
        for item in draft.get("items", []):
            legacy_items.append({
                "product_id": item["product_id"],
                "suggested_qty": item.get("suggested_qty", 0),
                "rate_mt": item.get("rate_mt"),
                "rate_mt_weighted": item.get("rate_mt_weighted"),
                "rate_source": item.get("rate_source"),
                "confidence_score": item.get("confidence_score"),
                "trend": item.get("trend"),
                "formula_version": item.get("formula_version"),
                "pre_clamp_need_qty": item.get("pre_clamp_need_qty"),
                "final_need_qty": item.get("final_need_qty"),
                "abandoned": item.get("abandoned"),
                "abandoned_reason": item.get("abandoned_reason"),
                "expected_depletion_days": item.get("expected_depletion_days"),
                "coverage_days": item.get("coverage_days"),
                "was_clamped": item.get("was_clamped"),
                "clamp_reason": item.get("clamp_reason"),
                "max_safe_qty": item.get("max_safe_qty"),
                "rate_used": item.get("rate_used"),
                "weekly_multiplier": item.get("weekly_multiplier"),
                "weekly_multiplier_source": item.get("weekly_multiplier_source"),
                "supply_days": item.get("supply_days"),
                "days_to_next_route": item.get("days_to_next_route"),
                "interval_count": item.get("interval_count"),
                "last_delivery_qty": item.get("last_delivery_qty"),
                "last_delivery_date": item.get("last_delivery_date"),
                "risk_score": item.get("risk_score"),
                "priority_rank": item.get("priority_rank", 0),
                "flags": item.get("flags", {})
            })
        
        draft_doc = {
            "customer_id": customer_id,
            "generated_from": source,
            "items": legacy_items,
            "route_info": draft.get("route_info"),
            "calculation_params": draft.get("calculation_params"),
            "updated_at": to_iso(now)
        }
        
        await db[COL_SYSTEM_DRAFTS].update_one(
            {"customer_id": customer_id},
            {"$set": draft_doc, "$setOnInsert": {"created_at": to_iso(now)}},
            upsert=True
        )
        
        return draft_doc
    
    @classmethod
    async def process_delivery(
        cls,
        customer_id: str,
        product_id: str,
        delivery_date: str,
        delivery_qty: float
    ) -> None:
        """
        Yeni teslimat geldiğinde state'i güncelle.
        
        Args:
            customer_id: Müşteri ID'si
            product_id: Ürün ID'si
            delivery_date: Teslimat tarihi
            delivery_qty: Teslimat miktarı
        """
        now = now_utc()
        delivery_dt = parse_date(delivery_date)
        
        # Mevcut state
        state = await db[COL_DE_STATE].find_one(
            {"customer_id": customer_id, "product_id": product_id}
        )
        
        if state:
            await cls._update_existing_state(state, delivery_date, delivery_qty, delivery_dt, now)
        else:
            await cls._create_new_state(customer_id, product_id, delivery_date, delivery_qty, now)
        
        # Draft'ı güncelle
        await cls.save(customer_id, "delivery_event")
    
    # =========================================================================
    # PRIVATE METHODS - Data Fetching
    # =========================================================================
    
    @classmethod
    async def _get_product_states(cls, customer_id: str) -> List[dict]:
        """Müşterinin aktif ürün durumlarını getir."""
        cursor = db[COL_DE_STATE].find(
            {"customer_id": customer_id, "is_active": True},
            {"_id": 0}
        )
        return await cursor.to_list(length=500)
    
    @classmethod
    async def _get_products(cls, product_ids: List[str]) -> Dict[str, dict]:
        """Ürün bilgilerini getir."""
        cursor = db[COL_PRODUCTS].find(
            {"product_id": {"$in": product_ids}},
            {"_id": 0}
        )
        products = await cursor.to_list(length=500)
        return {p["product_id"]: p for p in products}

    @classmethod
    async def _get_customer_product_consumptions(cls, customer_id: str) -> Dict[str, dict]:
        """Yeni aggregate consumption verisini product_id bazında getir."""
        cursor = db[COLL_CUSTOMER_PRODUCT_CONSUMPTIONS].find(
            {"customer_id": customer_id},
            {"_id": 0}
        )
        items = await cursor.to_list(length=500)
        return {item["product_id"]: item for item in items}
    
    @classmethod
    async def _get_weekly_multipliers(cls, today, customer: dict, product_ids: List[str]) -> Dict[str, dict]:
        """Haftalık çarpanları fallback zinciri ile getir."""
        week_start = today - timedelta(days=today.weekday())
        cursor = db[COL_DE_MULTIPLIERS].find(
            {"week_start": week_start.isoformat(), "product_id": {"$in": product_ids}},
            {"_id": 0}
        ).sort([("updated_at", -1), ("created_at", -1)])
        records = await cursor.to_list(length=500)

        depot_id = customer.get("depot_id") or customer.get("depo_id")
        segment_id = customer.get("segment_id") or customer.get("customer_type") or customer.get("channel") or customer.get("segment")

        result = {}
        for product_id in product_ids:
            result[product_id] = cls._resolve_weekly_multiplier_for_product(records, depot_id, segment_id, product_id)
        return result

    @classmethod
    def _resolve_weekly_multiplier_for_product(cls, records: List[dict], depot_id: Optional[str], segment_id: Optional[str], product_id: str) -> dict:
        if depot_id and segment_id:
            for record in records:
                if (
                    record.get("product_id") == product_id and
                    record.get("depot_id") == depot_id and
                    record.get("segment_id") == segment_id
                ):
                    return {"multiplier": record.get("multiplier", 1.0), "source": "depot_segment_product"}

        if segment_id:
            for record in records:
                if (
                    record.get("product_id") == product_id and
                    record.get("segment_id") == segment_id and
                    not record.get("depot_id")
                ):
                    return {"multiplier": record.get("multiplier", 1.0), "source": "segment_product"}

        for record in records:
            if (
                record.get("product_id") == product_id and
                not record.get("segment_id") and
                not record.get("depot_id")
            ):
                return {"multiplier": record.get("multiplier", 1.0), "source": "product_only"}

        return {"multiplier": 1.0, "source": "default"}
    
    # =========================================================================
    # PRIVATE METHODS - Calculation
    # =========================================================================
    
    @classmethod
    def _calculate_item(
        cls,
        product_id: str,
        state: Optional[dict],
        aggregate: Optional[dict],
        products: Dict[str, dict],
        multipliers: Dict[str, float],
        route_info: dict,
        today
    ) -> dict:
        """Tek bir ürün için dual-read hesaplama yap."""
        pid = product_id
        state = state or {}
        aggregate = aggregate or {}
        product = products.get(pid, {})

        prev_delivery_qty = state.get("prev_delivery_qty")
        prev_delivery_date = state.get("prev_delivery_date")
        last_delivery_date = aggregate.get("last_invoice_date") or state.get("last_delivery_date")
        last_delivery_qty = aggregate.get("last_quantity") or state.get("last_delivery_qty")
        interval_rates = state.get("interval_rates", [])
        interval_count = aggregate.get("interval_count", state.get("interval_count", 0))
        confidence_score = aggregate.get("confidence_score")
        if confidence_score is None:
            confidence_score = min(1, interval_count / 5) if interval_count else 0.0
        trend = aggregate.get("trend", "stable")
        rate_mt_weighted = aggregate.get("rate_mt_weighted")

        multiplier_info = multipliers.get(pid, {"multiplier": 1.0, "source": "default"})
        weekly_multiplier = multiplier_info.get("multiplier", 1.0)
        weekly_multiplier_source = multiplier_info.get("source", "default")

        rate_mt = state.get("rate_mt")
        if rate_mt is None and interval_rates:
            rates_to_use = interval_rates[-SMA_WINDOW:]
            rate_mt = sum(rates_to_use) / len(rates_to_use) if rates_to_use else None

        if not rate_mt_weighted:
            rate_mt_weighted = None

        if rate_mt_weighted is not None:
            rate_base = rate_mt_weighted
            rate_source = "aggregate"
        else:
            rate_base = rate_mt
            rate_source = "state"

        rate_used = rate_base * weekly_multiplier if rate_base else None

        pre_clamp_need_qty = None
        final_need_qty = None
        if rate_used and rate_used > EPSILON:
            pre_clamp_need_qty = round(rate_used * route_info["days_to_next_route"], 2)
            final_need_qty = pre_clamp_need_qty

        last_dt = parse_date(last_delivery_date)
        days_since_last = (today - last_dt).days if last_dt else None

        expected_depletion_days = aggregate.get("expected_depletion_days")
        if expected_depletion_days is None and rate_used and rate_used > EPSILON and last_delivery_qty:
            expected_depletion_days = round(last_delivery_qty / rate_used, 2)

        abandoned = False
        abandoned_reason = None
        if (
            rate_used and rate_used > EPSILON and
            last_delivery_qty and
            last_delivery_date and
            days_since_last is not None and
            expected_depletion_days is not None
        ):
            if days_since_last > expected_depletion_days * 3:
                abandoned = True
                abandoned_reason = "days_since_last_delivery exceeded expected_depletion_days * 3"
                final_need_qty = None

        estimated_depletion = None
        if expected_depletion_days and last_dt:
            estimated_depletion = (today + timedelta(days=expected_depletion_days)).isoformat()

        coverage_days = aggregate.get("coverage_days")
        if coverage_days is None and pre_clamp_need_qty and rate_used and rate_used > EPSILON:
            coverage_days = round(pre_clamp_need_qty / rate_used, 2)

        was_clamped = False
        clamp_reason = None
        max_safe_qty = None
        if (
            not abandoned and
            final_need_qty is not None and
            rate_used and rate_used > EPSILON and
            product.get("shelf_life_days")
        ):
            max_safe_qty = round(rate_used * product["shelf_life_days"], 2)
            if coverage_days and coverage_days > product["shelf_life_days"]:
                final_need_qty = round(min(final_need_qty, max_safe_qty), 2)
                was_clamped = True
                clamp_reason = "coverage_days exceeded shelf_life_days"

        risk_score = None
        if rate_used and rate_used > EPSILON and last_delivery_qty:
            days_stock_lasts = last_delivery_qty / rate_used
            risk_score = round(days_stock_lasts - route_info["days_to_next_route"], 2)

        delivery_count = state.get("delivery_count", aggregate.get("invoice_count", 0))
        age_days = state.get("age_days", 0)

        if delivery_count <= 1:
            maturity_mode, maturity_label = "first_time", "İlk Sipariş"
        elif interval_count >= 8 and age_days >= 365:
            maturity_mode, maturity_label = "mature", "Olgun"
        else:
            maturity_mode, maturity_label = "young", "Gelişen"

        skt_risk = False
        if product.get("shelf_life_days") and coverage_days:
            if coverage_days > product["shelf_life_days"] / 2:
                skt_risk = True

        return {
            "product_id": pid,
            "product_name": product.get("name", pid),
            "product_code": pid,
            "prev_delivery_qty": prev_delivery_qty,
            "prev_delivery_date": prev_delivery_date,
            "last_delivery_date": last_delivery_date,
            "last_delivery_qty": last_delivery_qty,
            "interval_rates": interval_rates[-3:],
            "interval_count": interval_count,
            "rate_mt": round(rate_mt, 4) if rate_mt else None,
            "rate_mt_weighted": round(rate_mt_weighted, 4) if rate_mt_weighted else None,
            "rate_source": rate_source,
            "confidence_score": round(confidence_score, 4) if confidence_score is not None else None,
            "trend": trend,
            "weekly_multiplier": round(weekly_multiplier, 2),
            "weekly_multiplier_source": weekly_multiplier_source,
            "rate_used": round(rate_used, 4) if rate_used else None,
            "supply_days": route_info["supply_days"],
            "days_to_next_route": route_info["days_to_next_route"],
            "suggested_qty": final_need_qty or 0,
            "need_qty": final_need_qty,
            "pre_clamp_need_qty": pre_clamp_need_qty,
            "final_need_qty": final_need_qty,
            "days_since_last_delivery": days_since_last,
            "estimated_depletion_at": estimated_depletion,
            "expected_depletion_days": expected_depletion_days,
            "coverage_days": coverage_days,
            "shelf_life_days": product.get("shelf_life_days"),
            "was_clamped": was_clamped,
            "clamp_reason": clamp_reason,
            "max_safe_qty": max_safe_qty,
            "abandoned": abandoned,
            "abandoned_reason": abandoned_reason,
            "risk_score": risk_score,
            "maturity_mode": maturity_mode,
            "maturity_label": maturity_label,
            "formula_version": "v2-dual-read",
            "flags": {
                "skt_risk": skt_risk,
                "low_data": interval_count < 3,
                "new_product": delivery_count <= 1,
                "low_confidence": confidence_score < 0.4 or interval_count < 1,
            },
            "priority_rank": 0
        }
    
    @classmethod
    def _empty_draft(cls, customer_id: str, customer: dict, route_info: dict, now) -> dict:
        """Boş draft oluştur."""
        return {
            "customer_id": customer_id,
            "customer_name": customer.get("name", ""),
            "route_days": customer.get("route_plan", {}).get("days", []),
            "route_info": route_info,
            "items": [],
            "summary": {
                "total_products": 0,
                "total_need_qty": 0,
                "products_with_data": 0,
                "products_low_data": 0
            },
            "generated_at": to_iso(now),
            "generated_from": "draft_engine_v2"
        }
    
    # =========================================================================
    # PRIVATE METHODS - State Management
    # =========================================================================
    
    @classmethod
    async def _update_existing_state(cls, state: dict, delivery_date: str, delivery_qty: float, delivery_dt, now):
        """Mevcut state'i güncelle."""
        prev_date = parse_date(state.get("last_delivery_date"))
        prev_qty = state.get("last_delivery_qty")
        
        # Yeni interval rate hesapla
        new_rate = None
        if prev_date and prev_qty and delivery_dt:
            days_between = (delivery_dt - prev_date).days
            if days_between > 0:
                new_rate = prev_qty / days_between
        
        # interval_rates güncelle
        interval_rates = state.get("interval_rates", [])
        if new_rate is not None:
            interval_rates.append(round(new_rate, 4))
            interval_rates = interval_rates[-SMA_WINDOW:]
        
        # Yeni rate_mt
        rate_mt = sum(interval_rates) / len(interval_rates) if interval_rates else None
        
        # Route bilgisi
        customer = await db[COL_CUSTOMERS].find_one({"id": state["customer_id"]}, {"_id": 0})
        route_days = customer.get("route_plan", {}).get("days", []) if customer else []
        route_info = get_route_info(route_days)
        
        # need_qty
        multiplier = state.get("weekly_multiplier", 1.0)
        need_qty = round(rate_mt * multiplier * route_info["supply_days"], 2) if rate_mt else None
        
        # Age days
        first_seen = parse_date(state.get("first_seen_at"))
        age_days = (now.date() - first_seen).days if first_seen else 0
        
        update_data = {
            "prev_delivery_date": state.get("last_delivery_date"),
            "prev_delivery_qty": state.get("last_delivery_qty"),
            "last_delivery_date": delivery_date,
            "last_delivery_qty": delivery_qty,
            "delivery_count": state.get("delivery_count", 0) + 1,
            "interval_count": len(interval_rates),
            "interval_rates": interval_rates,
            "rate_mt": round(rate_mt, 4) if rate_mt else None,
            "rate_used": round(rate_mt * multiplier, 4) if rate_mt else None,
            "need_qty": need_qty,
            "supply_days": route_info["supply_days"],
            "days_to_next_route": route_info["days_to_next_route"],
            "age_days": age_days,
            "last_seen_at": delivery_date,
            "updated_at": to_iso(now)
        }
        
        await db[COL_DE_STATE].update_one(
            {"_id": state["_id"]},
            {"$set": update_data}
        )
    
    @classmethod
    async def _create_new_state(cls, customer_id: str, product_id: str, delivery_date: str, delivery_qty: float, now):
        """Yeni state oluştur."""
        new_state = {
            "customer_id": customer_id,
            "product_id": product_id,
            "first_seen_at": delivery_date,
            "last_seen_at": delivery_date,
            "delivery_count": 1,
            "last_delivery_date": delivery_date,
            "last_delivery_qty": delivery_qty,
            "prev_delivery_date": None,
            "prev_delivery_qty": None,
            "interval_count": 0,
            "interval_rates": [],
            "rate_mt": None,
            "weekly_multiplier": 1.0,
            "rate_used": None,
            "need_qty": None,
            "is_active": True,
            "created_at": to_iso(now),
            "updated_at": to_iso(now)
        }
        await db[COL_DE_STATE].insert_one(new_state)


# Backward compatibility alias
DraftService = DraftEngine
