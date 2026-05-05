from config.database import db
from repositories.gib_import_repository import GIBImportRepository
from services.gib_import.constants import (
    IMPORT_STATUS_COMPLETED,
    IMPORT_STATUS_FAILED,
    IMPORT_STATUS_RUNNING,
    INVOICE_STATUS_IMPORTED,
)
from services.gib_import.errors import GibPortalError
from services.gib_import.live_gib_adapter import LiveGibAdapter
from services.gib_import.mock_gib_adapter import MockGibAdapter
from services.gib_import.parser_adapter import GIBHtmlParserAdapter


class GIBImportService:
    """Coordinates mock/live GİB import and idempotent invoice ingestion."""

    def __init__(self, adapter_factory=None):
        self.repository = GIBImportRepository(db)
        self.parser = GIBHtmlParserAdapter()
        self.adapter_factory = adapter_factory or {
            'mock': MockGibAdapter,
            'live': LiveGibAdapter,
        }

    def _build_lookup_query(self, salesperson_id: str, invoice_payload: dict) -> dict:
        if invoice_payload.get('ettn'):
            return {'ettn': invoice_payload['ettn']}
        return {
            'salesperson_id': salesperson_id,
            'invoice_number': invoice_payload.get('invoice_number'),
            'invoice_date': invoice_payload.get('invoice_date'),
            'identity_number': invoice_payload.get('identity_number'),
        }

    def _get_adapter(self, mode: str):
        adapter_class = self.adapter_factory.get(mode)
        if not adapter_class:
            raise GibPortalError('invalid_mode', f'Unsupported import mode: {mode}', 400)
        return adapter_class()

    async def start_import(self, salesperson_id: str, mode: str = 'mock', date_from: str | None = None, date_to: str | None = None) -> dict:
        job = await self.repository.create_import_job(salesperson_id)
        try:
            await self.repository.update_import_job(job['id'], {
                'status': IMPORT_STATUS_RUNNING,
                'started_at': job['created_at'],
                'mode': mode,
                'parse_error_count': 0,
                'login_error_count': 0,
                'portal_changed': False,
                'skipped_count': 0,
                'imported_invoice_count': 0,
            })

            adapter = self._get_adapter(mode)
            if mode == 'live':
                raw_payloads = await adapter.fetch_payloads(
                    salesperson_id=salesperson_id,
                    date_from=date_from,
                    date_to=date_to,
                )
            else:
                raw_payloads = await adapter.fetch_payloads()

            imported_invoices = []
            skipped_missing_identity = 0
            parse_error_count = 0

            for raw_payload in raw_payloads:
                try:
                    parsed = self.parser.parse(raw_payload['html_content'])
                except Exception:
                    parse_error_count += 1
                    continue

                invoice_data = parsed['invoice']
                if not invoice_data.get('identity_number'):
                    skipped_missing_identity += 1
                    continue

                invoice_doc = {
                    'salesperson_id': salesperson_id,
                    'import_job_id': job['id'],
                    'customer_id': None,
                    'draft_customer_id': None,
                    'ettn': invoice_data.get('ettn'),
                    'invoice_number': invoice_data.get('invoice_number'),
                    'invoice_date': invoice_data.get('invoice_date'),
                    'business_name': invoice_data.get('business_name') or 'Bilinmeyen İşletme',
                    'tax_no': invoice_data.get('tax_no'),
                    'tc_no': invoice_data.get('tc_no'),
                    'identity_number': invoice_data['identity_number'],
                    'currency': 'TRY',
                    'grand_total': invoice_data.get('grand_total', 0.0),
                    'raw_ref': {
                        'source': adapter.source,
                        'source_key': raw_payload['source_key'],
                        'import_job_id': job['id'],
                    },
                    'raw_payload': {
                        'html_content': raw_payload['html_content'],
                    },
                    'status': INVOICE_STATUS_IMPORTED,
                    'is_cancelled': False,
                }

                lookup_query = self._build_lookup_query(salesperson_id, invoice_data)
                invoice_result = await self.repository.upsert_invoice(invoice_doc, lookup_query)
                stored_invoice = invoice_result['document']
                for line in parsed['lines']:
                    await self.repository.upsert_product_catalog_entry(line)
                await self.repository.replace_invoice_lines(stored_invoice['id'], parsed['lines'])
                imported_invoices.append(stored_invoice)

            await self.repository.update_import_job(job['id'], {
                'status': IMPORT_STATUS_COMPLETED,
                'finished_at': job['created_at'],
                'invoice_count': len(imported_invoices),
                'raw_payload_count': len(raw_payloads),
                'skipped_missing_identity': skipped_missing_identity,
                'skipped_count': skipped_missing_identity,
                'imported_invoice_count': len(imported_invoices),
                'parse_error_count': parse_error_count,
            })

            return {
                'job_id': job['id'],
                'status': IMPORT_STATUS_COMPLETED,
                'mode': mode,
                'invoice_count': len(imported_invoices),
                'raw_payload_count': len(raw_payloads),
                'skipped_missing_identity': skipped_missing_identity,
                'parse_error_count': parse_error_count,
            }
        except GibPortalError as exc:
            await self.repository.update_import_job(job['id'], {
                'status': IMPORT_STATUS_FAILED,
                'finished_at': job['created_at'],
                'error_message': exc.code,
                'login_error_count': 1 if exc.code in {'invalid_credentials', 'captcha_required', 'otp_required', 'session_expired'} else 0,
                'portal_changed': exc.code == 'portal_layout_changed',
            })
            raise
        except Exception as exc:
            await self.repository.update_import_job(job['id'], {
                'status': IMPORT_STATUS_FAILED,
                'finished_at': job['created_at'],
                'error_message': str(exc),
            })
            raise
