"""Idempotent Mongo collection + index bootstrap for GİB import domain.

Usage:
  cd /app/backend
  python scripts/dev/bootstrap_gib_import_collections.py
"""

import sys
from pathlib import Path

from pymongo import MongoClient, ASCENDING
from dotenv import dotenv_values

sys.path.insert(0, str(Path('/app/backend')))

from services.gib_import.constants import (
    COLL_SALESPERSONS,
    COLL_DRAFT_CUSTOMERS,
    COLL_CUSTOMERS,
    COLL_CUSTOMER_USERS,
    COLL_INVOICES,
    COLL_INVOICE_LINES,
    COLL_PRODUCTS,
    COLL_PRODUCT_ALIASES,
    COLL_CUSTOMER_PRODUCT_CONSUMPTIONS,
    COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS,
    COLL_GIB_IMPORT_JOBS,
)

CFG = dotenv_values('/app/backend/.env')
CLIENT = MongoClient(CFG['MONGO_URL'])
DB = CLIENT[CFG['DB_NAME']]


def ensure_collection(name: str):
    if name not in DB.list_collection_names():
        DB.create_collection(name)


def main():
    collections = [
        COLL_SALESPERSONS,
        COLL_DRAFT_CUSTOMERS,
        COLL_CUSTOMERS,
        COLL_CUSTOMER_USERS,
        COLL_INVOICES,
        COLL_INVOICE_LINES,
        COLL_PRODUCTS,
        COLL_PRODUCT_ALIASES,
        COLL_CUSTOMER_PRODUCT_CONSUMPTIONS,
        COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS,
        COLL_GIB_IMPORT_JOBS,
    ]

    for name in collections:
        ensure_collection(name)

    # salespersons
    DB[COLL_SALESPERSONS].create_index([('id', ASCENDING)], name='uq_salespersons_id', unique=True)
    DB[COLL_SALESPERSONS].create_index([('user_id', ASCENDING)], name='uq_salespersons_user_id', unique=True, sparse=True)
    DB[COLL_SALESPERSONS].create_index([('tax_no', ASCENDING)], name='ix_salespersons_tax_no', sparse=True)

    # draft_customers
    DB[COLL_DRAFT_CUSTOMERS].create_index(
        [('salesperson_id', ASCENDING), ('identity_number', ASCENDING)],
        name='uq_draft_customers_salesperson_identity',
        unique=True,
    )
    DB[COLL_DRAFT_CUSTOMERS].create_index([('draft_status', ASCENDING)], name='ix_draft_customers_status')
    DB[COLL_DRAFT_CUSTOMERS].create_index([('last_invoice_date', ASCENDING)], name='ix_draft_customers_last_invoice_date')
    DB[COLL_DRAFT_CUSTOMERS].create_index([('business_name', ASCENDING)], name='ix_draft_customers_business_name')

    # customers
    DB[COLL_CUSTOMERS].create_index([('id', ASCENDING)], name='uq_customers_id', unique=True)
    DB[COLL_CUSTOMERS].create_index(
        [('salesperson_id', ASCENDING), ('identity_number', ASCENDING)],
        name='uq_customers_salesperson_identity',
        unique=True,
    )
    DB[COLL_CUSTOMERS].create_index([('draft_customer_id', ASCENDING)], name='ix_customers_draft_customer_id', sparse=True)
    DB[COLL_CUSTOMERS].create_index([('business_name', ASCENDING)], name='ix_customers_business_name')

    # customer_users
    DB[COLL_CUSTOMER_USERS].create_index([('id', ASCENDING)], name='uq_customer_users_id', unique=True)
    DB[COLL_CUSTOMER_USERS].create_index([('username', ASCENDING)], name='uq_customer_users_username', unique=True)
    DB[COLL_CUSTOMER_USERS].create_index([('customer_id', ASCENDING)], name='uq_customer_users_customer_id', unique=True)
    DB[COLL_CUSTOMER_USERS].create_index([('must_change_password', ASCENDING)], name='ix_customer_users_password_change')

    # invoices
    DB[COLL_INVOICES].create_index([('id', ASCENDING)], name='uq_invoices_id', unique=True)
    DB[COLL_INVOICES].create_index([('ettn', ASCENDING)], name='uq_invoices_ettn', unique=True, sparse=True)
    DB[COLL_INVOICES].create_index([('salesperson_id', ASCENDING), ('identity_number', ASCENDING)], name='ix_invoices_salesperson_identity')
    DB[COLL_INVOICES].create_index([('invoice_date', ASCENDING)], name='ix_invoices_invoice_date')
    DB[COLL_INVOICES].create_index([('customer_id', ASCENDING)], name='ix_invoices_customer_id', sparse=True)
    DB[COLL_INVOICES].create_index([('draft_customer_id', ASCENDING)], name='ix_invoices_draft_customer_id', sparse=True)
    DB[COLL_INVOICES].create_index([('import_job_id', ASCENDING)], name='ix_invoices_import_job_id', sparse=True)

    # invoice_lines
    DB[COLL_INVOICE_LINES].create_index([('id', ASCENDING)], name='uq_invoice_lines_id', unique=True)
    DB[COLL_INVOICE_LINES].create_index([('invoice_id', ASCENDING), ('line_no', ASCENDING)], name='uq_invoice_lines_invoice_line', unique=True)
    DB[COLL_INVOICE_LINES].create_index([('product_id', ASCENDING)], name='ix_invoice_lines_product_id', sparse=True)
    DB[COLL_INVOICE_LINES].create_index([('normalized_name', ASCENDING)], name='ix_invoice_lines_normalized_name')

    # products
    DB[COLL_PRODUCTS].create_index([('normalized_name', ASCENDING)], name='ix_products_normalized_name', sparse=True)
    DB[COLL_PRODUCTS].create_index([('product_code', ASCENDING)], name='ix_products_product_code', sparse=True)

    # product_aliases
    DB[COLL_PRODUCT_ALIASES].create_index([('id', ASCENDING)], name='uq_product_aliases_id', unique=True)
    DB[COLL_PRODUCT_ALIASES].create_index([('normalized_alias', ASCENDING)], name='uq_product_aliases_normalized_alias', unique=True)
    DB[COLL_PRODUCT_ALIASES].create_index([('product_id', ASCENDING)], name='ix_product_aliases_product_id')

    # customer_product_consumptions
    DB[COLL_CUSTOMER_PRODUCT_CONSUMPTIONS].create_index([('id', ASCENDING)], name='uq_customer_product_consumptions_id', unique=True)
    DB[COLL_CUSTOMER_PRODUCT_CONSUMPTIONS].create_index(
        [('customer_id', ASCENDING), ('product_id', ASCENDING)],
        name='uq_customer_product_consumptions_customer_product',
        unique=True,
    )
    DB[COLL_CUSTOMER_PRODUCT_CONSUMPTIONS].create_index([('daily_consumption', ASCENDING)], name='ix_customer_product_consumptions_daily_consumption', sparse=True)
    DB[COLL_CUSTOMER_PRODUCT_CONSUMPTIONS].create_index([('last_invoice_date', ASCENDING)], name='ix_customer_product_consumptions_last_invoice_date', sparse=True)

    # customer_product_daily_consumptions
    DB[COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS].create_index(
        [('customer_id', ASCENDING), ('product_id', ASCENDING), ('date', ASCENDING)],
        name='uq_customer_product_daily_consumptions_customer_product_date',
        unique=True,
    )
    DB[COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS].create_index([('customer_id', ASCENDING), ('date', ASCENDING)], name='ix_customer_product_daily_consumptions_customer_date')
    DB[COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS].create_index([('product_id', ASCENDING), ('date', ASCENDING)], name='ix_customer_product_daily_consumptions_product_date')

    # gib_import_jobs
    DB[COLL_GIB_IMPORT_JOBS].create_index([('id', ASCENDING)], name='uq_gib_import_jobs_id', unique=True)
    DB[COLL_GIB_IMPORT_JOBS].create_index([('salesperson_id', ASCENDING), ('created_at', ASCENDING)], name='ix_gib_import_jobs_salesperson_created_at')
    DB[COLL_GIB_IMPORT_JOBS].create_index([('status', ASCENDING)], name='ix_gib_import_jobs_status')

    print('GIB import collections and indexes ensured successfully.')


if __name__ == '__main__':
    main()
