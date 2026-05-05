from fastapi import APIRouter, Depends

from models.user import UserRole
from utils.auth import require_role
from services.seftali.core import std_resp
from services.seftali.campaign_service import CampaignService

router = APIRouter(prefix="/sales", tags=["Seftali-Sales-Campaigns"])

SALES_ROLES = [UserRole.SALES_REP, UserRole.SALES_AGENT]


@router.get("/campaigns")
async def list_campaigns(current_user=Depends(require_role(SALES_ROLES))):
    """Plasiyer için aktif kampanyaları listele."""
    campaigns = await CampaignService.list_campaigns()
    return std_resp(True, campaigns)
