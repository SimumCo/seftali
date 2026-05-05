"""
Users Management Routes - Admin için kullanıcı CRUD işlemleri
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from models.user import User, UserRole
from utils.auth import get_current_user, require_role, hash_password
from config.database import db
import uuid
from datetime import datetime, timezone

router = APIRouter(prefix="/users", tags=["Users Management"])


@router.get("", response_model=List[dict])
async def get_all_users(
    role: Optional[str] = None,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    query = {}
    if role:
        query["role"] = role
    users = await db.users.find(query, {"_id": 0, "password_hash": 0}).to_list(length=1000)
    return users


@router.get("/{user_id}")
async def get_user_by_id(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/create")
async def create_user(
    user_data: dict,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    existing = await db.users.find_one({"username": user_data.get("username")})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    if "password" in user_data:
        user_data["password_hash"] = hash_password(user_data["password"])
        del user_data["password"]
    else:
        raise HTTPException(status_code=400, detail="Password is required")

    if "id" not in user_data:
        user_data["id"] = str(uuid.uuid4())
    if "created_at" not in user_data:
        user_data["created_at"] = datetime.now(timezone.utc).isoformat()
    if "is_active" not in user_data:
        user_data["is_active"] = True

    await db.users.insert_one(user_data)
    user_data.pop("password_hash", None)
    user_data.pop("_id", None)

    return {"message": "User created successfully", "user": user_data}


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    update_data: dict,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    allowed_fields = ['username', 'full_name', 'email', 'phone', 'role',
                      'is_active', 'address', 'customer_number', 'channel_type']
    update_fields = {k: v for k, v in update_data.items() if k in allowed_fields}

    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")

    if 'username' in update_fields and update_fields['username'] != user.get('username'):
        existing = await db.users.find_one({"username": update_fields['username']})
        if existing:
            raise HTTPException(status_code=400, detail="Username already exists")

    await db.users.update_one({"id": user_id}, {"$set": update_fields})
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})

    return {"message": "User updated successfully", "user": updated_user}


@router.put("/{user_id}/password")
async def change_user_password(
    user_id: str,
    password_data: dict,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    new_password = password_data.get("new_password")
    if not new_password or len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"password_hash": hash_password(new_password)}}
    )
    return {"message": "Password changed successfully", "username": user.get("username")}


@router.delete("/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.users.update_one({"id": user_id}, {"$set": {"is_active": False}})
    return {"message": "User deleted successfully (deactivated)", "username": user.get("username")}


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.users.update_one({"id": user_id}, {"$set": {"is_active": True}})
    return {"message": "User activated successfully", "username": user.get("username")}


@router.delete("/{user_id}/permanent")
async def permanently_delete_user(
    user_id: str,
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=500, detail="Failed to delete user")

    return {"message": "User permanently deleted", "username": user.get("username")}


@router.get("/stats/summary")
async def get_users_stats(
    current_user: User = Depends(require_role([UserRole.ADMIN]))
):
    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"is_active": True})
    inactive_users = await db.users.count_documents({"is_active": False})

    roles_cursor = db.users.aggregate([
        {"$group": {"_id": "$role", "count": {"$sum": 1}}}
    ])
    roles_data = await roles_cursor.to_list(length=None)
    role_counts = {item["_id"]: item["count"] for item in roles_data}

    return {
        "total_users": total_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "by_role": role_counts
    }
