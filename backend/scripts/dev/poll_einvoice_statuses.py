"""Manual polling helper for queued/processing e-Fatura invoices.

Usage:
  cd /app/backend
  python scripts/dev/poll_einvoice_statuses.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path('/app/backend')))

from services.efatura.invoice_service import EInvoiceService
from repositories.efatura_repository import EInvoiceRepository
from services.efatura.provider_adapter import ProviderError


async def main():
    repository = EInvoiceRepository()
    service = EInvoiceService(repository=repository)
    pending = await repository.list_pending_for_polling(limit=100)
    results = []
    for invoice in pending:
        try:
            result = await service.refresh_status(invoice['id'])
            results.append({'invoice_id': invoice['id'], 'status': result.status})
        except ProviderError as exc:
            results.append({'invoice_id': invoice['id'], 'error': exc.message})
        except ValueError as exc:
            results.append({'invoice_id': invoice['id'], 'error': str(exc)})
    print(results)


if __name__ == '__main__':
    asyncio.run(main())
