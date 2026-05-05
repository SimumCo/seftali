from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel, field_validator
from models.user import UserRole
from utils.auth import require_role
from config.database import db
from services.seftali.core import (
    gen_id, now_utc, to_iso, std_resp,
    COL_CUSTOMERS, COL_PRODUCTS
)
from services.seftali.draft_engine import DraftEngine
from services.seftali.order_service import OrderService

router = APIRouter(prefix="/sales", tags=["Seftali-Sales"])

# NOTE:
# This module now intentionally holds legacy / ambiguous leftovers only.
# Clear domain slices have already been moved to dedicated modules:
# - smart_orders.py
# - stock.py
# - customers.py
# - orders.py
# Remaining handlers stay here until ownership is crystal clear.


SALES_ROLES = [UserRole.SALES_REP, UserRole.SALES_AGENT]


# ===========================
# EXTRA: PATCH /customers/{id} - Müşteri Güncelleme
# ===========================
class UpdateCustomerBody(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    channel: Optional[str] = None
    route_days: Optional[List[str]] = None


@router.patch("/customers/{customer_id}")
async def update_customer(customer_id: str, body: UpdateCustomerBody, current_user=Depends(require_role(SALES_ROLES))):
    """Müşteri bilgilerini günceller (plasiyer tarafından)"""
    
    # Müşteri var mı kontrol et
    customer = await db[COL_CUSTOMERS].find_one({"id": customer_id}, {"_id": 0})
    if not customer:
        raise HTTPException(404, "Müşteri bulunamadı")
    
    # Güncellenecek alanları hazırla
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
        # Rut günlerini route_plan içinde güncelle
        update_data["route_plan.days"] = body.route_days
    
    if not update_data:
        return std_resp(True, customer, "Güncellenecek alan yok")
    
    update_data["updated_at"] = to_iso(now_utc())
    
    await db[COL_CUSTOMERS].update_one(
        {"id": customer_id},
        {"$set": update_data}
    )
    
    # Rut günleri değiştiyse müşterinin draft'ını yeniden hesapla
    if body.route_days is not None:
        await DraftEngine.save(customer_id, "route_change")
    
    # Güncellenmiş müşteriyi döndür
    updated_customer = await db[COL_CUSTOMERS].find_one({"id": customer_id}, {"_id": 0})
    return std_resp(True, updated_customer, "Müşteri bilgileri güncellendi")


@router.get("/products")
async def list_products(current_user=Depends(require_role(SALES_ROLES))):
    cursor = db[COL_PRODUCTS].find({}, {"_id": 0})
    items = await cursor.to_list(length=500)
    return std_resp(True, items)


# ===========================
# Kampanya Siparişe Ekle
# ===========================
class CampaignOrderItem(BaseModel):
    campaign_id: str
    customer_id: str
    qty: int  # Kampanya miktarı


@router.post("/campaigns/add-to-order")
async def add_campaign_to_order(
    body: CampaignOrderItem,
    current_user=Depends(require_role(SALES_ROLES)),
):
    """
    Kampanyayı müşteri siparişine/working_copy'ye ekler.
    
    Kampanya türlerine göre:
    - discount: Sadece ürün eklenir (indirimli fiyatla)
    - gift: Ürün + hediye ürünü eklenir
    """
    from services.seftali.utils import now_utc, to_iso
    
    # Kampanya kontrolü
    campaign = await db["sf_campaigns"].find_one(
        {"id": body.campaign_id, "status": "active"},
        {"_id": 0}
    )
    if not campaign:
        raise HTTPException(404, "Kampanya bulunamadı veya aktif değil")
    
    # Müşteri kontrolü
    customer = await db[COL_CUSTOMERS].find_one(
        {"id": body.customer_id, "is_active": True},
        {"_id": 0}
    )
    if not customer:
        raise HTTPException(404, "Müşteri bulunamadı")
    
    # Minimum miktar kontrolü
    min_qty = campaign.get("min_qty", 1)
    if body.qty < min_qty:
        raise HTTPException(400, f"Minimum {min_qty} adet sipariş gerekli")
    
    now = now_utc()
    
    # Mevcut working_copy'yi al veya oluştur
    working_copy = await db["sf_working_copies"].find_one(
        {"customer_id": body.customer_id, "status": "active"},
        {"_id": 0}
    )
    
    items_to_add = []
    
    # Ana ürün
    main_item = {
        "product_id": campaign.get("product_id"),
        "product_name": campaign.get("product_name"),
        "qty": body.qty,
        "user_qty": body.qty,
        "unit_price": campaign.get("campaign_price") or campaign.get("normal_price"),
        "source": "campaign",
        "campaign_id": body.campaign_id,
        "campaign_title": campaign.get("title")
    }
    items_to_add.append(main_item)
    
    # Hediyeli kampanya ise hediye ürünü de ekle
    if campaign.get("type") == "gift" and campaign.get("gift_product_id"):
        gift_qty = campaign.get("gift_qty", 1) * (body.qty // min_qty)  # Her min_qty için 1 hediye
        gift_item = {
            "product_id": campaign.get("gift_product_id"),
            "product_name": campaign.get("gift_product_name"),
            "qty": gift_qty,
            "user_qty": gift_qty,
            "unit_price": 0,  # Hediye ücretsiz
            "source": "campaign_gift",
            "campaign_id": body.campaign_id,
            "campaign_title": campaign.get("title") + " (Hediye)"
        }
        items_to_add.append(gift_item)
    
    if working_copy:
        # Mevcut working_copy'ye ekle
        existing_items = working_copy.get("items", [])
        
        for new_item in items_to_add:
            # Aynı ürün var mı kontrol et
            found = False
            for i, ex_item in enumerate(existing_items):
                if ex_item.get("product_id") == new_item["product_id"]:
                    # Miktarı güncelle
                    existing_items[i]["qty"] = existing_items[i].get("qty", 0) + new_item["qty"]
                    existing_items[i]["user_qty"] = existing_items[i]["qty"]
                    found = True
                    break
            
            if not found:
                existing_items.append(new_item)
        
        await db["sf_working_copies"].update_one(
            {"customer_id": body.customer_id, "status": "active"},
            {
                "$set": {
                    "items": existing_items,
                    "updated_at": to_iso(now)
                }
            }
        )
    else:
        # Yeni working_copy oluştur
        new_working_copy = {
            "id": gen_id(),
            "customer_id": body.customer_id,
            "status": "active",
            "items": items_to_add,
            "created_at": to_iso(now),
            "updated_at": to_iso(now),
            "created_by": current_user.id
        }
        await db["sf_working_copies"].insert_one(new_working_copy)
    
    # Sonucu döndür
    result = {
        "customer_id": body.customer_id,
        "customer_name": customer.get("name"),
        "campaign_id": body.campaign_id,
        "campaign_title": campaign.get("title"),
        "items_added": items_to_add,
        "total_qty": sum(i["qty"] for i in items_to_add)
    }
    
    return std_resp(True, result, "Kampanya siparişe eklendi")


# ===========================
# PLASİYER SİPARİŞ HESAPLAMA
# ===========================


@router.get("/plasiyer/route-customers/{route_day}")
async def get_route_customers(
    route_day: str,
    current_user=Depends(require_role(SALES_ROLES))
):
    """Belirli bir rota gününün müşterilerini getir"""
    customers = await OrderService.get_route_customers(
        salesperson_id=current_user.id,
        route_day=route_day.upper()
    )
    
    # Her müşteri için sipariş durumunu ekle
    customer_ids = [c["id"] for c in customers]
    orders = await OrderService._get_customer_orders(customer_ids)
    drafts = await OrderService._get_customer_drafts(customer_ids)
    
    for customer in customers:
        cid = customer["id"]
        if cid in orders:
            customer["order_status"] = "submitted"
            customer["order_items_count"] = len(orders[cid].get("items", []))
        elif cid in drafts:
            customer["order_status"] = "draft_available"
            customer["draft_items_count"] = len([i for i in drafts[cid].get("items", []) if i.get("suggested_qty", 0) > 0])
        else:
            customer["order_status"] = "no_order"
    
    return std_resp(True, customers)

