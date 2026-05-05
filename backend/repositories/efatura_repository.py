from datetime import datetime, timezone, timedelta
from typing import Optional
from pymongo import DESCENDING

from config.database import db


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class EInvoiceRepository:
    def __init__(self):
        self.invoices = db['invoices']
        self.logs = db['invoice_provider_logs']

    async def ensure_indexes(self):
        await self.invoices.create_index('local_reference_id', unique=True, sparse=True)
        await self.invoices.create_index('provider_invoice_id', sparse=True)
        await self.invoices.create_index('status')
        await self.invoices.create_index('next_status_check_at')
        await self.logs.create_index('invoice_id')
        await self.logs.create_index([('created_at', DESCENDING)])

    async def create_invoice(self, payload: dict):
        await self.invoices.insert_one(payload)
        return payload

    async def get_invoice(self, invoice_id: str):
        return await self.invoices.find_one({'id': invoice_id}, {'_id': 0})

    async def find_by_local_reference_id(self, local_reference_id: str):
        return await self.invoices.find_one({'local_reference_id': local_reference_id}, {'_id': 0})

    async def update_invoice(self, invoice_id: str, updates: dict):
        updates['updated_at'] = now_iso()
        await self.invoices.update_one({'id': invoice_id}, {'$set': updates})
        return await self.get_invoice(invoice_id)

    async def insert_provider_log(self, payload: dict):
        await self.logs.insert_one(payload)

    async def list_pending_for_polling(self, now_value: Optional[str] = None, limit: int = 100):
        now_value = now_value or now_iso()
        cursor = self.invoices.find(
            {
                'provider_name': 'turkcell_esirket',
                'status': {'$in': ['queued', 'processing']},
                '$or': [
                    {'next_status_check_at': {'$exists': False}},
                    {'next_status_check_at': None},
                    {'next_status_check_at': {'$lte': now_value}},
                ],
            },
            {'_id': 0},
        ).sort('updated_at', 1).limit(limit)
        return await cursor.to_list(length=limit)
