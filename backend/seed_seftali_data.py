"""SEFTALI modülü için seed scripti - PostgreSQL JSONB adaptörü ile çalışır."""
import asyncio
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from config.database import db
from utils.auth import hash_password
import uuid


def gid():
    return str(uuid.uuid4())


def iso(dt):
    return dt.isoformat()


NOW = datetime.now(timezone.utc)


async def main():
    print("=" * 60)
    print("SEFTALI SEED BAŞLIYOR (PostgreSQL)")
    print("=" * 60)

    # ---- 1. Demo kullanıcılar ----
    print("\n1. Kullanıcılar...")
    demo_users = [
        {"username": "admin", "full_name": "Sistem Yöneticisi", "role": "admin", "pw": "admin123",
         "email": "admin@seftali.com"},
        {"username": "muhasebe", "full_name": "Muhasebe Personeli", "role": "accounting", "pw": "muhasebe123",
         "email": "muhasebe@seftali.com"},
        {"username": "sf_musteri", "full_name": "Müşteri A - Market", "role": "customer", "pw": "musteri123",
         "email": "musteria@seftali.com"},
        {"username": "sf_musteri2", "full_name": "Müşteri B - Restoran", "role": "customer", "pw": "musteri123",
         "email": "musterib@seftali.com"},
        {"username": "sf_satici", "full_name": "Şeftali Satıcı", "role": "sales_rep", "pw": "satici123",
         "email": "satici@seftali.com"},
        {"username": "plasiyer1", "full_name": "Plasiyer 1", "role": "sales_agent", "pw": "plasiyer123",
         "email": "plasiyer@seftali.com"},
    ]
    user_ids = {}
    for u in demo_users:
        existing = await db['users'].find_one({"username": u["username"]})
        if existing:
            user_ids[u["username"]] = existing["id"]
            print(f"   - {u['username']} mevcut")
        else:
            uid = gid()
            await db['users'].insert_one({
                "id": uid, "username": u["username"], "password_hash": hash_password(u["pw"]),
                "full_name": u["full_name"], "email": u["email"], "phone": "",
                "role": u["role"], "is_active": True,
                "created_at": iso(NOW),
            })
            user_ids[u["username"]] = uid
            print(f"   + {u['username']} oluşturuldu ({u['role']})")

    # ---- 2. Ürünler ----
    print("\n2. Ürünler...")
    products = [
        {"id": gid(), "code": "AYR_BRD", "name": "Ayran Bardak", "shelf_life_days": 21, "unit": "adet", "price": 5.0},
        {"id": gid(), "code": "YOG_KOV", "name": "Yoğurt Kova", "shelf_life_days": 28, "unit": "kg", "price": 45.0},
        {"id": gid(), "code": "SUZ_YOG", "name": "Süzme Yoğurt", "shelf_life_days": 14, "unit": "kg", "price": 65.0},
        {"id": gid(), "code": "AYR_PET", "name": "Ayran Pet Şişe", "shelf_life_days": 30, "unit": "adet", "price": 8.0},
        {"id": gid(), "code": "SUT_LT",  "name": "Süt 1 Litre",   "shelf_life_days": 7,  "unit": "lt",   "price": 25.0},
    ]
    existing_count = await db['sf_products'].count_documents({})
    if existing_count == 0:
        for p in products:
            p["created_at"] = iso(NOW)
            p["updated_at"] = iso(NOW)
            p["is_active"] = True
            await db['sf_products'].insert_one(p)
        print(f"   + {len(products)} ürün oluşturuldu")
    else:
        print(f"   - {existing_count} ürün mevcut")

    prod_map = {}
    for p in await db['sf_products'].find({}).to_list(100):
        prod_map[p["code"]] = p["id"]

    # ---- 3. Müşteriler ----
    print("\n3. Müşteriler...")
    cust_a_id = gid()
    cust_b_id = gid()
    sf_customers = [
        {
            "id": cust_a_id, "user_id": user_ids["sf_musteri"],
            "name": "Müşteri A - Market",
            "route_plan": {"days": ["MON", "FRI"], "effective_from_week": "2025-W01"},
            "is_active": True, "created_at": iso(NOW), "updated_at": iso(NOW),
        },
        {
            "id": cust_b_id, "user_id": user_ids["sf_musteri2"],
            "name": "Müşteri B - Restoran",
            "route_plan": {"days": ["TUE", "THU"], "effective_from_week": "2025-W01"},
            "is_active": True, "created_at": iso(NOW), "updated_at": iso(NOW),
        },
    ]
    existing_custs = await db['sf_customers'].count_documents({})
    if existing_custs == 0:
        for c in sf_customers:
            await db['sf_customers'].insert_one(c)
        print(f"   + {len(sf_customers)} müşteri oluşturuldu")
    else:
        print(f"   - {existing_custs} müşteri mevcut")
        c = await db['sf_customers'].find_one({"user_id": user_ids["sf_musteri"]})
        if c:
            cust_a_id = c["id"]

    # ---- 4. Örnek teslimatlar ----
    print("\n4. Teslimatlar...")
    existing_dlv = await db['sf_deliveries'].count_documents({})
    if existing_dlv == 0:
        seven_days_ago = NOW - timedelta(days=7)
        two_days_ago = NOW - timedelta(days=2)
        deliveries = [
            {
                "id": gid(), "customer_id": cust_a_id,
                "created_by_salesperson_id": user_ids["sf_satici"],
                "delivery_type": "route", "delivered_at": iso(seven_days_ago),
                "invoice_no": "FTR-001", "acceptance_status": "pending",
                "accepted_at": None, "rejected_at": None, "rejection_reason": None,
                "items": [
                    {"product_id": prod_map.get("AYR_BRD", ""), "qty": 100},
                    {"product_id": prod_map.get("YOG_KOV", ""), "qty": 20},
                ],
                "created_at": iso(seven_days_ago), "updated_at": iso(seven_days_ago),
            },
            {
                "id": gid(), "customer_id": cust_a_id,
                "created_by_salesperson_id": user_ids["sf_satici"],
                "delivery_type": "route", "delivered_at": iso(two_days_ago),
                "invoice_no": "FTR-002", "acceptance_status": "pending",
                "accepted_at": None, "rejected_at": None, "rejection_reason": None,
                "items": [
                    {"product_id": prod_map.get("AYR_BRD", ""), "qty": 60},
                    {"product_id": prod_map.get("SUZ_YOG", ""), "qty": 15},
                ],
                "created_at": iso(two_days_ago), "updated_at": iso(two_days_ago),
            },
            {
                "id": gid(), "customer_id": cust_a_id,
                "created_by_salesperson_id": user_ids["sf_satici"],
                "delivery_type": "off_route", "delivered_at": iso(NOW),
                "invoice_no": "FTR-003", "acceptance_status": "pending",
                "accepted_at": None, "rejected_at": None, "rejection_reason": None,
                "items": [
                    {"product_id": prod_map.get("AYR_PET", ""), "qty": 50},
                ],
                "created_at": iso(NOW), "updated_at": iso(NOW),
            },
        ]
        for d in deliveries:
            await db['sf_deliveries'].insert_one(d)
        print(f"   + {len(deliveries)} teslimat oluşturuldu")
    else:
        print(f"   - {existing_dlv} teslimat mevcut")

    # ---- 5. Sistem ayarları ----
    print("\n5. Sistem ayarları...")
    existing_settings = await db['sf_system_settings'].find_one({"type": "order_settings"})
    if not existing_settings:
        await db['sf_system_settings'].insert_one({
            "id": gid(), "type": "order_settings",
            "order_cutoff_hour": 16, "order_cutoff_minute": 30,
            "auto_draft_enabled": True,
            "created_at": iso(NOW),
        })
        print("   + Order settings oluşturuldu")
    else:
        print("   - Order settings mevcut")

    print("\n" + "=" * 60)
    print("SEED TAMAMLANDI!")
    print("=" * 60)
    print("\nGiriş bilgileri:")
    print("  Admin:     admin / admin123")
    print("  Muhasebe:  muhasebe / muhasebe123")
    print("  Müşteri A: sf_musteri / musteri123")
    print("  Müşteri B: sf_musteri2 / musteri123")
    print("  Satıcı:    sf_satici / satici123")
    print("  Plasiyer:  plasiyer1 / plasiyer123")


if __name__ == "__main__":
    asyncio.run(main())
