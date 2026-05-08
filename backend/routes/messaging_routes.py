from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime, timezone
import uuid

from config.database import db
from models.user import User, UserRole
from utils.auth import get_current_user, require_role

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationCreateRequest(BaseModel):
    user_id: Optional[str] = None
    target_roles: Optional[List[str]] = None
    type: str
    title: str
    message: str
    related_order_id: Optional[str] = None
    related_campaign_id: Optional[str] = None


@router.get("")
async def get_notifications(
    is_read: Optional[bool] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_user)
):
    query: dict = {"user_id": current_user.id}
    if is_read is not None:
        query["is_read"] = is_read

    cursor = db.notifications.find(query, {"_id": 0}).sort("created_at", -1)
    notifications = await cursor.to_list(limit)
    return notifications


@router.get("/unread-count")
async def get_unread_count(current_user: User = Depends(get_current_user)):
    cursor = db.notifications.find({"user_id": current_user.id, "is_read": False}, {"_id": 0})
    items = await cursor.to_list(10000)
    return {"count": len(items)}


@router.put("/read-all")
async def mark_all_as_read_put(current_user: User = Depends(get_current_user)):
    await db.notifications.update_many(
        {"user_id": current_user.id, "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True, "message": "Tüm bildirimler okundu olarak işaretlendi"}


@router.post("/mark-all-read")
async def mark_all_as_read_post(current_user: User = Depends(get_current_user)):
    await db.notifications.update_many(
        {"user_id": current_user.id, "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True, "message": "Tüm bildirimler okundu olarak işaretlendi"}


@router.post("/create")
async def create_notification(
    data: NotificationCreateRequest,
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.ACCOUNTING]))
):
    target_user_ids: List[str] = []

    if data.user_id:
        target_user_ids = [data.user_id]
    elif data.target_roles:
        cursor = db.users.find(
            {"role": {"$in": data.target_roles}, "is_active": True}, {"_id": 0}
        )
        users = await cursor.to_list(1000)
        target_user_ids = [u["id"] for u in users]
    else:
        raise HTTPException(status_code=400, detail="user_id veya target_roles belirtilmeli")

    created_ids = []
    for uid in target_user_ids:
        notification = {
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "type": data.type,
            "title": data.title,
            "message": data.message,
            "is_read": False,
            "related_order_id": data.related_order_id,
            "related_campaign_id": data.related_campaign_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.notifications.insert_one(notification)
        created_ids.append(notification["id"])

    return {"success": True, "created": len(created_ids), "ids": created_ids}


@router.put("/{notification_id}/read")
async def mark_as_read_put(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    notif = await db.notifications.find_one({"id": notification_id}, {"_id": 0})
    if not notif:
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı")
    if notif.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Bu bildirimi okuma yetkiniz yok")

    await db.notifications.update_one(
        {"id": notification_id},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True}


@router.post("/{notification_id}/mark-read")
async def mark_as_read_post(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    notif = await db.notifications.find_one({"id": notification_id}, {"_id": 0})
    if not notif:
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı")
    if notif.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Bu bildirimi okuma yetkiniz yok")

    await db.notifications.update_one(
        {"id": notification_id},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    return {"success": True}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user)
):
    notif = await db.notifications.find_one({"id": notification_id}, {"_id": 0})
    if not notif:
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı")
    if notif.get("user_id") != current_user.id:
        raise HTTPException(status_code=403, detail="Bu bildirimi silme yetkiniz yok")

    await db.notifications.delete_one({"id": notification_id})
    return {"success": True}
