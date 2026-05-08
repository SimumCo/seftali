"""Bildirim endpoint'leri."""
from datetime import datetime, timezone
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from config.database import db
from models.user import User
from utils.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationCreateRequest(BaseModel):
    user_id: Optional[str] = None
    type: str
    title: str
    message: str
    related_order_id: Optional[str] = None
    related_campaign_id: Optional[str] = None


@router.get("")
async def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    unread_only: bool = Query(default=False),
    current_user: User = Depends(get_current_user),
):
    query = {"user_id": current_user.id}
    if unread_only:
        query["is_read"] = False

    items = await db.notifications.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(length=limit)
    return {"data": items, "count": len(items)}


@router.get("/unread-count")
async def get_unread_count(current_user: User = Depends(get_current_user)):
    count = await db.notifications.count_documents({"user_id": current_user.id, "is_read": False})
    return {"count": count}


@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı")
    return {"success": True}


@router.post("/{notification_id}/mark-read")
async def mark_read_post(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    result = await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı")
    return {"success": True}


@router.put("/read-all")
async def mark_all_as_read(current_user: User = Depends(get_current_user)):
    result = await db.notifications.update_many(
        {"user_id": current_user.id, "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"updated": result.modified_count}


@router.post("/mark-all-read")
async def mark_all_read_post(current_user: User = Depends(get_current_user)):
    result = await db.notifications.update_many(
        {"user_id": current_user.id, "is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"updated": result.modified_count}


@router.delete("/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    result = await db.notifications.delete_one({"id": notification_id, "user_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Bildirim bulunamadı")
    return {"success": True}


@router.post("/create")
async def create_notification_endpoint(
    payload: NotificationCreateRequest,
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin", "accounting"):
        raise HTTPException(status_code=403, detail="Yetkisiz")

    target_user_id = payload.user_id or current_user.id
    notification = {
        "id": str(uuid.uuid4()),
        "user_id": target_user_id,
        "type": payload.type,
        "title": payload.title,
        "message": payload.message,
        "is_read": False,
        "related_order_id": payload.related_order_id,
        "related_campaign_id": payload.related_campaign_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.notifications.insert_one(notification)
    return notification
