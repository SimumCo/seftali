from datetime import datetime, timedelta

from config.database import db
from services.seftali.core import (
    COL_CUSTOMERS,
    COL_DELIVERIES,
    COL_ORDERS,
    get_product_by_id,
    now_utc,
    to_iso,
)
from services.seftali.draft_engine import DraftEngine


class CustomerService:
    """Thin façade for customer-related sales endpoints."""

    @classmethod
    async def list_customers(cls) -> list:
        cursor = db[COL_CUSTOMERS].find({"is_active": True}, {"_id": 0})
        return await cursor.to_list(length=500)

    @classmethod
    async def get_customer_consumption(cls, customer_id: str) -> dict | None:
        customer = await db[COL_CUSTOMERS].find_one({"id": customer_id}, {"_id": 0})
        if not customer:
            return None

        pipeline = [
            {"$match": {"customer_id": customer_id}},
            {"$group": {
                "_id": "$product_id",
                "total_consumption": {"$sum": "$consumption"},
                "daily_avg": {"$avg": "$consumption"},
                "record_count": {"$sum": 1},
                "first_date": {"$min": "$date"},
                "last_date": {"$max": "$date"},
            }},
            {"$sort": {"daily_avg": -1}},
        ]

        results = await db["sf_daily_consumption"].aggregate(pipeline).to_list(50)

        consumption_data = []
        for result in results:
            product_id = result.pop("_id")
            product = await get_product_by_id(db, product_id)
            consumption_data.append({
                "product_id": product_id,
                "product_name": product.get("name", "Bilinmeyen") if product else "Bilinmeyen",
                "product_code": product.get("code", "") if product else "",
                "daily_avg": round(result["daily_avg"], 2),
                "total_consumption": round(result["total_consumption"], 2),
                "record_count": result["record_count"],
                "first_date": result["first_date"],
                "last_date": result["last_date"],
            })

        return {
            "customer_id": customer_id,
            "customer_name": customer.get("name"),
            "products": consumption_data,
            "total_products": len(consumption_data),
        }

    @classmethod
    async def get_customers_summary(cls) -> list:
        cursor = db[COL_CUSTOMERS].find({"is_active": True}, {"_id": 0})
        customers = await cursor.to_list(length=500)

        customer_summaries = []
        for customer in customers:
            customer_id = customer["id"]

            pending_orders = await db[COL_ORDERS].find({
                "customer_id": customer_id,
                "status": {"$in": ["submitted", "approved"]}
            }, {"_id": 0, "id": 1, "status": 1, "items": 1, "created_at": 1}).to_list(length=50)

            total_orders = await db[COL_ORDERS].count_documents({"customer_id": customer_id})
            last_delivery = await db[COL_DELIVERIES].find_one(
                {"customer_id": customer_id, "acceptance_status": "accepted"},
                {"_id": 0, "delivered_at": 1, "items": 1}
            )

            seven_days_ago = (datetime.utcnow() - timedelta(days=7)).isoformat() + "Z"
            overdue_deliveries = await db[COL_DELIVERIES].count_documents({
                "customer_id": customer_id,
                "acceptance_status": "pending",
                "delivered_at": {"$lt": seven_days_ago}
            })

            total_deliveries = await db[COL_DELIVERIES].count_documents({"customer_id": customer_id})
            last_order = await db[COL_ORDERS].find_one(
                {"customer_id": customer_id},
                {"_id": 0, "created_at": 1}
            )

            days_since_last_order = None
            if last_order:
                try:
                    last_date = datetime.fromisoformat(last_order["created_at"].replace("Z", "+00:00"))
                    days_since_last_order = (datetime.now(last_date.tzinfo) - last_date).days
                except Exception:
                    pass

            customer_summaries.append({
                **customer,
                "pending_orders_count": len(pending_orders),
                "pending_orders": pending_orders[:3],
                "total_orders": total_orders,
                "overdue_deliveries_count": overdue_deliveries,
                "total_deliveries": total_deliveries,
                "last_delivery_date": last_delivery.get("delivered_at") if last_delivery else None,
                "last_order_date": last_order.get("created_at") if last_order else None,
                "days_since_last_order": days_since_last_order,
            })

        return customer_summaries

    @classmethod
    async def update_customer(cls, customer_id: str, body) -> tuple[dict | None, str]:
        customer = await db[COL_CUSTOMERS].find_one({"id": customer_id}, {"_id": 0})
        if not customer:
            return None, "Müşteri bulunamadı"

        update_data = {}
        if body.name is not None:
            update_data["name"] = body.name
        if body.code is not None:
            update_data["code"] = body.code
        if body.phone is not None:
            update_data["phone"] = body.phone
        if body.email is not None:
            update_data["email"] = body.email
        if body.address is not None:
            update_data["address"] = body.address
        if body.channel is not None:
            update_data["channel"] = body.channel
        if body.route_days is not None:
            update_data["route_plan.days"] = body.route_days

        if not update_data:
            return customer, "Güncellenecek alan yok"

        update_data["updated_at"] = to_iso(now_utc())
        await db[COL_CUSTOMERS].update_one({"id": customer_id}, {"$set": update_data})

        if body.route_days is not None:
            await DraftEngine.save(customer_id, "route_change")

        updated_customer = await db[COL_CUSTOMERS].find_one({"id": customer_id}, {"_id": 0})
        return updated_customer, "Müşteri bilgileri güncellendi"
