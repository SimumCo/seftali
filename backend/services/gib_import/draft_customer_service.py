from config.database import db
from repositories.gib_import_repository import GIBImportRepository
from services.gib_import.constants import DRAFT_STATUS_PENDING


class DraftCustomerService:
    """Aggregates imported invoices into draft customer records."""

    def __init__(self):
        self.repository = GIBImportRepository(db)

    async def aggregate_from_invoices(self, salesperson_id: str) -> dict:
        invoices = await self.repository.list_invoices_for_salesperson(salesperson_id)
        grouped = {}

        for invoice in invoices:
            identity_number = invoice.get('tc_no') or invoice.get('tax_no') or invoice.get('identity_number')
            if not identity_number:
                continue

            bucket = grouped.setdefault(identity_number, {
                'business_name': invoice.get('business_name') or 'Bilinmeyen İşletme',
                'tax_number': invoice.get('tax_no'),
                'tc_no': invoice.get('tc_no'),
                'identity_number': identity_number,
                'invoice_count': 0,
                'first_invoice_date': invoice.get('invoice_date'),
                'last_invoice_date': invoice.get('invoice_date'),
                'total_amount': 0.0,
                'source_invoice_ids': [],
                'status': DRAFT_STATUS_PENDING,
            })

            bucket['invoice_count'] += 1
            bucket['total_amount'] += float(invoice.get('grand_total') or 0)
            bucket['source_invoice_ids'].append(invoice['id'])

            invoice_date = invoice.get('invoice_date')
            if invoice_date and (not bucket['first_invoice_date'] or invoice_date < bucket['first_invoice_date']):
                bucket['first_invoice_date'] = invoice_date
            if invoice_date and (not bucket['last_invoice_date'] or invoice_date > bucket['last_invoice_date']):
                bucket['last_invoice_date'] = invoice_date
            if invoice.get('business_name'):
                bucket['business_name'] = invoice['business_name']
            if invoice.get('tax_no'):
                bucket['tax_number'] = invoice['tax_no']
            if invoice.get('tc_no'):
                bucket['tc_no'] = invoice['tc_no']

        upserted = []
        for identity_number, payload in grouped.items():
            result = await self.repository.upsert_draft_customer(
                salesperson_id=salesperson_id,
                identity_number=identity_number,
                payload=payload,
            )
            upserted.append(result['document'])

        return {
            'salesperson_id': salesperson_id,
            'draft_customer_count': len(upserted),
            'items': upserted,
        }

    async def list_draft_customers(self, salesperson_id: str) -> list:
        return await self.repository.list_draft_customers(salesperson_id)
