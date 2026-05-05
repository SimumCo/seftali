from config.database import db


class CampaignService:
    """Thin façade for sales campaign listing."""

    @classmethod
    async def list_campaigns(cls) -> list:
        cursor = db['sf_campaigns'].find({'status': 'active'}, {'_id': 0}).sort('created_at', -1)
        return await cursor.to_list(length=50)
