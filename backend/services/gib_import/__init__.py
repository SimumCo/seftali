"""GİB import domain package.

This package is intentionally isolated from the current working ŞEFTALİ flow.
Batch 1 only establishes:
- collection names
- contracts / schemas
- bootstrap / index creation
- service skeletons

Live GİB login/sync implementation is deferred.
"""

from .constants import (
    COLL_SALESPERSONS,
    COLL_DRAFT_CUSTOMERS,
    COLL_CUSTOMERS,
    COLL_CUSTOMER_USERS,
    COLL_INVOICES,
    COLL_INVOICE_LINES,
    COLL_PRODUCTS,
    COLL_PRODUCT_ALIASES,
    COLL_CUSTOMER_PRODUCT_CONSUMPTIONS,
    COLL_GIB_IMPORT_JOBS,
)

__all__ = [
    'COLL_SALESPERSONS',
    'COLL_DRAFT_CUSTOMERS',
    'COLL_CUSTOMERS',
    'COLL_CUSTOMER_USERS',
    'COLL_INVOICES',
    'COLL_INVOICE_LINES',
    'COLL_PRODUCTS',
    'COLL_PRODUCT_ALIASES',
    'COLL_CUSTOMER_PRODUCT_CONSUMPTIONS',
    'COLL_GIB_IMPORT_JOBS',
]
