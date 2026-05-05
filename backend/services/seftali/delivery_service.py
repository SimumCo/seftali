from config.database import db
from services.seftali.core import gen_id, now_utc, to_iso, COL_CUSTOMERS, COL_DELIVERIES


class DeliveryService:
    """Thin façade for sales delivery endpoints."""

    @classmethod
    async def create_delivery(cls, customer_id: str, delivery_type: str, delivered_at: str | None, invoice_no: str | None, items: list, salesperson_id: str) -> tuple[dict | None, str]:
        customer = await db[COL_CUSTOMERS].find_one({"id": customer_id, "is_active": True}, {"_id": 0})
        if not customer:
            return None, "Musteri bulunamadi"

        now = now_utc()
        delivery = {
            "id": gen_id(),
            "customer_id": customer_id,
            "created_by_salesperson_id": salesperson_id,
            "delivery_type": delivery_type,
            "delivered_at": delivered_at or to_iso(now),
            "invoice_no": invoice_no,
            "acceptance_status": "pending",
            "accepted_at": None,
            "rejected_at": None,
            "rejection_reason": None,
            "items": items,
            "created_at": to_iso(now),
            "updated_at": to_iso(now),
        }
        await db[COL_DELIVERIES].insert_one(delivery)
        delivery.pop("_id", None)
        return delivery, "Teslimat olusturuldu (pending)"

    @classmethod
    async def list_deliveries(cls, status: str | None = None, from_date: str | None = None, to_date: str | None = None) -> list:
        filt = {}
        if status:
            filt["acceptance_status"] = status
        if from_date or to_date:
            filt["delivered_at"] = {}
            if from_date:
                filt["delivered_at"]["$gte"] = from_date
            if to_date:
                filt["delivered_at"]["$lte"] = to_date

        cursor = db[COL_DELIVERIES].find(filt, {"_id": 0}).sort("delivered_at", -1)
        items = await cursor.to_list(length=200)
        for delivery in items:
            customer = await db[COL_CUSTOMERS].find_one({"id": delivery["customer_id"]}, {"_id": 0, "name": 1})
            if customer:
                delivery["customer_name"] = customer["name"]
        return items
