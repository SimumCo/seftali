from datetime import datetime, timezone
import uuid

from pymongo import UpdateOne

from repositories.base_repository import BaseRepository
from services.gib_import.constants import (
    COLL_CUSTOMERS,
    COLL_CUSTOMER_PRODUCT_CONSUMPTIONS,
    COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS,
    COLL_CUSTOMER_USERS,
    COLL_DRAFT_CUSTOMERS,
    COLL_GIB_IMPORT_JOBS,
    COLL_INVOICE_LINES,
    COLL_INVOICES,
    COLL_PRODUCT_ALIASES,
    COLL_PRODUCTS,
    IMPORT_STATUS_PENDING,
)
from services.seftali.core import COL_CUSTOMERS as COLL_SF_CUSTOMERS, COL_USERS as COLL_USERS


def _now_iso():
    return datetime.now(timezone.utc).isoformat()


def _id():
    return str(uuid.uuid4())


class GIBImportRepository:
    def __init__(self, db):
        self.jobs = BaseRepository(db, COLL_GIB_IMPORT_JOBS)
        self.invoices = BaseRepository(db, COLL_INVOICES)
        self.invoice_lines = BaseRepository(db, COLL_INVOICE_LINES)
        self.draft_customers = BaseRepository(db, COLL_DRAFT_CUSTOMERS)
        self.db = db

    async def create_import_job(self, salesperson_id: str) -> dict:
        job = {
            'id': _id(),
            'salesperson_id': salesperson_id,
            'status': IMPORT_STATUS_PENDING,
            'started_at': None,
            'finished_at': None,
            'invoice_count': 0,
            'raw_payload_count': 0,
            'error_message': None,
            'created_at': _now_iso(),
            'updated_at': _now_iso(),
        }
        await self.jobs.collection.insert_one(job)
        return job

    async def update_import_job(self, job_id: str, updates: dict):
        updates['updated_at'] = _now_iso()
        await self.jobs.collection.update_one({'id': job_id}, {'$set': updates})

    async def upsert_invoice(self, invoice_doc: dict, lookup_query: dict) -> dict:
        existing = await self.invoices.find_one(lookup_query, projection={'_id': 0})
        now = _now_iso()
        if existing:
            updates = {**invoice_doc, 'updated_at': now}
            await self.invoices.collection.update_one({'id': existing['id']}, {'$set': updates})
            merged = {**existing, **updates}
            return {'document': merged, 'created': False}

        doc = {
            'id': _id(),
            **invoice_doc,
            'created_at': now,
            'updated_at': now,
        }
        await self.invoices.collection.insert_one(doc)
        return {'document': doc, 'created': True}

    async def replace_invoice_lines(self, invoice_id: str, lines: list):
        await self.invoice_lines.collection.delete_many({'invoice_id': invoice_id})
        if not lines:
            return
        now = _now_iso()
        payload = [
            {
                'id': _id(),
                'invoice_id': invoice_id,
                'product_id': line.get('product_id'),
                'line_no': line['line_no'],
                'product_code': line.get('product_code'),
                'product_name': line['product_name'],
                'normalized_name': line['normalized_name'],
                'quantity': line['quantity'],
                'unit_price': line['unit_price'],
                'line_total': line['line_total'],
                'created_at': now,
                'updated_at': now,
            }
            for line in lines
        ]
        await self.invoice_lines.collection.insert_many(payload)

    async def upsert_product_catalog_entry(self, line: dict, session=None):
        product_id = line.get('product_id')
        if not product_id:
            return None
        now = _now_iso()
        await self.db[COLL_PRODUCTS].update_one(
            {'product_id': product_id},
            {
                '$set': {
                    'product_code': line.get('product_code'),
                    'name': line.get('product_name') or product_id,
                    'normalized_name': line.get('normalized_name'),
                    'updated_at': now,
                },
                '$setOnInsert': {
                    'id': _id(),
                    'created_at': now,
                    'is_active': True,
                },
            },
            upsert=True,
            session=session,
        )
        normalized_alias = line.get('normalized_name')
        if normalized_alias:
            await self.db[COLL_PRODUCT_ALIASES].update_one(
                {'normalized_alias': normalized_alias},
                {
                    '$set': {
                        'product_id': product_id,
                        'alias': line.get('product_name') or product_id,
                        'normalized_alias': normalized_alias,
                        'updated_at': now,
                    },
                    '$setOnInsert': {
                        'id': _id(),
                        'created_at': now,
                    },
                },
                upsert=True,
                session=session,
            )
        return product_id

    async def list_invoices_for_salesperson(self, salesperson_id: str) -> list:
        return await self.invoices.find_many(
            {'salesperson_id': salesperson_id},
            projection={'_id': 0},
            limit=5000,
            sort=[('invoice_date', 1)],
        )

    async def upsert_draft_customer(self, salesperson_id: str, identity_number: str, payload: dict):
        existing = await self.draft_customers.find_one(
            {'salesperson_id': salesperson_id, 'identity_number': identity_number},
            projection={'_id': 0},
        )
        now = _now_iso()
        if existing:
            updates = {**payload, 'updated_at': now}
            await self.draft_customers.collection.update_one({'id': existing['id']}, {'$set': updates})
            return {'document': {**existing, **updates}, 'created': False}

        doc = {
            'id': _id(),
            'salesperson_id': salesperson_id,
            **payload,
            'created_at': now,
            'updated_at': now,
        }
        await self.draft_customers.collection.insert_one(doc)
        return {'document': doc, 'created': True}

    async def find_customer_by_id(self, customer_id: str, session=None):
        return await self.db[COLL_CUSTOMERS].find_one({'id': customer_id}, {'_id': 0}, session=session)

    async def find_sf_customer_by_customer_id(self, customer_id: str, session=None):
        return await self.db[COLL_SF_CUSTOMERS].find_one({'customer_id': customer_id}, {'_id': 0}, session=session)

    async def find_sf_customer_by_identity(self, salesperson_id: str, identity_number: str, session=None):
        query = {
            'salesperson_id': salesperson_id,
            '$or': [
                {'identity_number': identity_number},
                {'tax_no': identity_number},
                {'tc_no': identity_number},
            ],
        }
        return await self.db[COLL_SF_CUSTOMERS].find_one(query, {'_id': 0}, session=session)

    async def insert_sf_customer(self, payload: dict, session=None):
        await self.db[COLL_SF_CUSTOMERS].insert_one(payload, session=session)
        return payload

    async def update_sf_customer(self, sf_customer_id: str, updates: dict, session=None):
        updates['updated_at'] = _now_iso()
        await self.db[COLL_SF_CUSTOMERS].update_one({'id': sf_customer_id}, {'$set': updates}, session=session)

    async def find_salesperson_user(self, salesperson_id: str, session=None):
        return await self.db[COLL_USERS].find_one({'id': salesperson_id}, {'_id': 0}, session=session)

    async def find_sf_customer_context(self, salesperson_id: str, session=None):
        return await self.db[COLL_SF_CUSTOMERS].find_one(
            {'salesperson_id': salesperson_id, 'is_active': True},
            {'_id': 0},
            sort=[('updated_at', -1), ('created_at', -1)],
            session=session,
        )

    async def find_draft_customer_by_id(self, draft_customer_id: str, session=None):
        return await self.draft_customers.collection.find_one({'id': draft_customer_id}, {'_id': 0}, session=session)

    async def find_customer_by_identity(self, identity_number: str, session=None):
        query = {
            '$or': [
                {'identity_number': identity_number},
                {'tax_no': identity_number},
                {'tc_no': identity_number},
            ]
        }
        return await self.db[COLL_CUSTOMERS].find_one(query, {'_id': 0}, session=session)

    async def find_customer_user_by_username(self, username: str, session=None):
        return await self.db[COLL_CUSTOMER_USERS].find_one({'username': username}, {'_id': 0}, session=session)

    async def find_customer_user_by_id(self, user_id: str, session=None):
        return await self.db[COLL_CUSTOMER_USERS].find_one({'id': user_id}, {'_id': 0}, session=session)

    async def update_customer_user(self, user_id: str, updates: dict, session=None):
        updates['updated_at'] = _now_iso()
        await self.db[COLL_CUSTOMER_USERS].update_one({'id': user_id}, {'$set': updates}, session=session)

    async def insert_customer(self, payload: dict, session=None):
        await self.db[COLL_CUSTOMERS].insert_one(payload, session=session)
        return payload

    async def insert_customer_user(self, payload: dict, session=None):
        await self.db[COLL_CUSTOMER_USERS].insert_one(payload, session=session)
        return payload

    async def update_draft_customer(self, draft_customer_id: str, updates: dict, session=None):
        updates['updated_at'] = _now_iso()
        await self.draft_customers.collection.update_one({'id': draft_customer_id}, {'$set': updates}, session=session)

    async def list_invoices_by_salesperson_identity(self, salesperson_id: str, identity_number: str, session=None) -> list:
        cursor = self.invoices.collection.find(
            {'salesperson_id': salesperson_id, 'identity_number': identity_number},
            {'_id': 0},
            session=session,
        ).sort('invoice_date', 1)
        return await cursor.to_list(length=5000)

    async def update_invoice_customer_link(self, invoice_id: str, customer_id: str, session=None):
        await self.invoices.collection.update_one(
            {'id': invoice_id},
            {'$set': {'customer_id': customer_id, 'updated_at': _now_iso()}},
            session=session,
        )

    async def list_customer_invoices(self, customer_id: str, session=None) -> list:
        cursor = self.invoices.collection.find(
            {'customer_id': customer_id, 'is_cancelled': {'$ne': True}},
            {'_id': 0},
            session=session,
        ).sort('invoice_date', 1)
        return await cursor.to_list(length=5000)

    async def list_invoice_lines(self, invoice_ids: list[str], session=None) -> list:
        if not invoice_ids:
            return []
        cursor = self.invoice_lines.collection.find(
            {'invoice_id': {'$in': invoice_ids}},
            {'_id': 0},
            session=session,
        ).sort([('invoice_id', 1), ('line_no', 1)])
        return await cursor.to_list(length=10000)

    async def get_product_alias_map(self, session=None) -> dict:
        cursor = self.db[COLL_PRODUCT_ALIASES].find({}, {'_id': 0}, session=session)
        aliases = await cursor.to_list(length=5000)
        return {alias['normalized_alias']: alias['product_id'] for alias in aliases}

    async def get_products_by_ids(self, product_ids: list[str], session=None) -> dict:
        cursor = self.db[COLL_PRODUCTS].find({'$or': [{'id': {'$in': product_ids}}, {'product_id': {'$in': product_ids}}]}, {'_id': 0}, session=session)
        products = await cursor.to_list(length=5000)
        result = {}
        for product in products:
            if product.get('id') in product_ids:
                result[product['id']] = product
            if product.get('product_id') in product_ids:
                result[product['product_id']] = product
        return result

    async def upsert_customer_product_consumption(self, customer_id: str, product_id: str, payload: dict, session=None):
        existing = await self.db[COLL_CUSTOMER_PRODUCT_CONSUMPTIONS].find_one(
            {'customer_id': customer_id, 'product_id': product_id},
            {'_id': 0},
            session=session,
        )
        now = _now_iso()
        if existing:
            await self.db[COLL_CUSTOMER_PRODUCT_CONSUMPTIONS].update_one(
                {'id': existing['id']},
                {'$set': {**payload, 'updated_at': now}},
                session=session,
            )
            return {'created': False, 'id': existing['id']}

        doc = {
            'id': _id(),
            'customer_id': customer_id,
            'product_id': product_id,
            **payload,
            'created_at': now,
            'updated_at': now,
        }
        await self.db[COLL_CUSTOMER_PRODUCT_CONSUMPTIONS].insert_one(doc, session=session)
        return {'created': True, 'id': doc['id']}

    async def delete_customer_product_daily_consumptions(self, customer_id: str, product_id: str | None = None, session=None):
        query = {'customer_id': customer_id}
        if product_id is not None:
            query['product_id'] = product_id
        await self.db[COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS].delete_many(query, session=session)

    async def upsert_customer_product_daily_consumption(self, row: dict, session=None):
        now = _now_iso()
        payload = {**row, 'updated_at': now}
        existing = await self.db[COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS].find_one(
            {'customer_id': row['customer_id'], 'product_id': row['product_id'], 'date': row['date']},
            {'_id': 0},
            session=session,
        )
        if existing:
            await self.db[COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS].update_one(
                {'id': existing['id']},
                {'$set': payload},
                session=session,
            )
            return {'created': False, 'id': existing['id']}

        doc = {'id': _id(), **payload, 'created_at': now}
        await self.db[COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS].insert_one(doc, session=session)
        return {'created': True, 'id': doc['id']}

    async def bulk_upsert_customer_product_daily_consumptions(self, rows: list[dict], session=None):
        if not rows:
            return {'created': 0, 'updated': 0}

        now = _now_iso()
        operations = []
        for row in rows:
            payload = {**row, 'updated_at': now}
            operations.append(
                UpdateOne(
                    {'customer_id': row['customer_id'], 'product_id': row['product_id'], 'date': row['date']},
                    {
                        '$set': payload,
                        '$setOnInsert': {'id': _id(), 'created_at': now},
                    },
                    upsert=True,
                )
            )
        result = await self.db[COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS].bulk_write(operations, ordered=False, session=session)
        return {
            'created': result.upserted_count,
            'updated': result.modified_count,
        }

    async def list_customer_product_daily_consumptions(self, customer_id: str, product_id: str | None = None, session=None) -> list:
        query = {'customer_id': customer_id}
        if product_id is not None:
            query['product_id'] = product_id
        cursor = self.db[COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS].find(query, {'_id': 0}, session=session).sort([('product_id', 1), ('date', 1)])
        return await cursor.to_list(length=20000)

    async def list_customer_product_consumptions(self, customer_id: str, session=None) -> list:
        cursor = self.db[COLL_CUSTOMER_PRODUCT_CONSUMPTIONS].find({'customer_id': customer_id}, {'_id': 0}, session=session)
        return await cursor.to_list(length=5000)

    async def list_draft_customers(self, salesperson_id: str) -> list:
        return await self.draft_customers.find_many(
            {'salesperson_id': salesperson_id},
            projection={'_id': 0},
            limit=1000,
            sort=[('last_invoice_date', -1)],
        )
