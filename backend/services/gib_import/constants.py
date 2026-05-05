"""Collection names and shared constants for GİB import flow."""

import os
from dotenv import dotenv_values

_ENV = dotenv_values('/app/backend/.env')

COLL_SALESPERSONS = 'salespersons'
COLL_DRAFT_CUSTOMERS = 'draft_customers'
COLL_CUSTOMERS = 'customers'
COLL_CUSTOMER_USERS = 'customer_users'
COLL_INVOICES = 'invoices'
COLL_INVOICE_LINES = 'invoice_lines'
COLL_PRODUCTS = 'products'
COLL_PRODUCT_ALIASES = 'product_aliases'
COLL_CUSTOMER_PRODUCT_CONSUMPTIONS = 'customer_product_consumptions'
COLL_CUSTOMER_PRODUCT_DAILY_CONSUMPTIONS = 'customer_product_daily_consumptions'
COLL_GIB_IMPORT_JOBS = 'gib_import_jobs'

DRAFT_STATUS_PENDING = 'review_pending'
DRAFT_STATUS_APPROVED = 'approved'
DRAFT_STATUS_REJECTED = 'rejected'

IMPORT_STATUS_PENDING = 'pending'
IMPORT_STATUS_RUNNING = 'running'
IMPORT_STATUS_COMPLETED = 'completed'
IMPORT_STATUS_FAILED = 'failed'

INVOICE_STATUS_IMPORTED = 'imported'
INVOICE_STATUS_LINKED = 'linked'
INVOICE_STATUS_CANCELLED = 'cancelled'

PASSWORD_CHANGE_REQUIRED = True
DEFAULT_CUSTOMER_PASSWORD = os.environ.get('DEFAULT_CUSTOMER_PASSWORD') or _ENV.get('DEFAULT_CUSTOMER_PASSWORD')

if not DEFAULT_CUSTOMER_PASSWORD:
    raise RuntimeError('DEFAULT_CUSTOMER_PASSWORD environment variable is required')
