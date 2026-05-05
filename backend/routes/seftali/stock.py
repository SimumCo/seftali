from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from models.user import UserRole
from utils.auth import require_role
from services.seftali.core import std_resp
from services.seftali.stock_service import StockService

router = APIRouter(prefix="/sales", tags=["Seftali-Sales-Stock"])

SALES_ROLES = [UserRole.SALES_REP, UserRole.SALES_AGENT]


class UpdateStockBody(BaseModel):
    items: List[dict]
    operation: str = "set"


@router.get("/plasiyer/stock")
async def get_plasiyer_stock(current_user=Depends(require_role(SALES_ROLES))):
    """Plasiyerin mevcut stoğunu getir"""
    result = await StockService.get_plasiyer_stock(current_user.id)
    if not result.get('success'):
        return std_resp(False, None, result.get('message', 'Stok kaydı bulunamadı'))
    return std_resp(True, result.get('data'))


@router.patch("/plasiyer/stock")
async def update_plasiyer_stock(
    body: UpdateStockBody,
    current_user=Depends(require_role(SALES_ROLES))
):
    """
    Plasiyer stoğunu güncelle.

    operation:
    - "set": Miktarı üzerine yaz
    - "add": Miktara ekle (depodan mal aldığında)
    - "subtract": Miktardan çıkar (müşteriye teslim ettiğinde)
    """
    result = await StockService.update_plasiyer_stock(
        salesperson_id=current_user.id,
        items=body.items,
        operation=body.operation,
    )

    if result.get('success'):
        return std_resp(True, result, 'Stok güncellendi')
    return std_resp(False, None, result.get('message', 'Hata oluştu'))
