from config.database import Database, db
from repositories.gib_import_repository import GIBImportRepository


class InvoiceLinkError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class InvoiceLinkService:
    """Links historical invoices to an approved customer."""

    def __init__(self):
        self.repository = GIBImportRepository(db)
        self.client = Database.get_client()

    async def link_customer_invoices(self, customer_id: str, salesperson_id: str) -> dict:
        try:
            async with await self.client.start_session() as session:
                async with session.start_transaction():
                    return await self._link_in_session(customer_id, salesperson_id, session)
        except InvoiceLinkError:
            raise
        except Exception as exc:
            if 'Transaction numbers are only allowed' in str(exc) or 'replica set' in str(exc).lower():
                return await self._link_in_session(customer_id, salesperson_id, session=None)
            raise

    async def _link_in_session(self, customer_id: str, salesperson_id: str, session=None) -> dict:
        customer = await self.repository.find_customer_by_id(customer_id, session=session)
        if not customer:
            raise InvoiceLinkError('Customer bulunamadı', 404)

        if customer.get('salesperson_id') != salesperson_id:
            raise InvoiceLinkError('Salesperson mismatch', 403)

        identity_number = customer.get('tc_no') or customer.get('tax_no') or customer.get('identity_number')
        if not identity_number:
            raise InvoiceLinkError('Customer identity missing', 400)

        invoices = await self.repository.list_invoices_by_salesperson_identity(salesperson_id, identity_number, session=session)

        linked_count = 0
        skipped_count = 0
        conflict_count = 0

        for invoice in invoices:
            current_customer_id = invoice.get('customer_id')
            if not current_customer_id:
                await self.repository.update_invoice_customer_link(invoice['id'], customer_id, session=session)
                linked_count += 1
                continue

            if current_customer_id == customer_id:
                skipped_count += 1
                continue

            conflict_count += 1

        return {
            'customer_id': customer_id,
            'linked_count': linked_count,
            'skipped_count': skipped_count,
            'conflict_count': conflict_count,
        }
