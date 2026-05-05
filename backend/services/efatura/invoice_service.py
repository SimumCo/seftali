import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

from .contracts import EInvoiceCreateRequest, EInvoiceCreateResult, EInvoiceStatusResult, EInvoiceStatus
from .provider_adapter import TurkcellEFaturaProviderAdapter, ProviderError
from .ubl_builder import UBLInvoiceBuilder, UBLGenerationError
from repositories.efatura_repository import EInvoiceRepository, now_iso


class EInvoiceService:
    PROVIDER_NAME = 'turkcell_esirket'
    SUPPLIER_VKN_TCKN = '1234567803'
    TEST_RECEIVER_VKN_TCKN = '1234567803'
    TEST_RECEIVER_ALIAS = 'urn:mail:defaulttest3pk@medyasoft.com.tr'

    def __init__(self, repository=None, provider=None, ubl_builder=None):
        self.repository = repository or EInvoiceRepository()
        self.provider = provider or TurkcellEFaturaProviderAdapter()
        self.ubl_builder = ubl_builder or UBLInvoiceBuilder(self.SUPPLIER_VKN_TCKN)

    def _build_invoice_document(self, payload: EInvoiceCreateRequest, ubl_xml: str) -> dict:
        now = now_iso()
        return {
            'id': str(uuid.uuid4()),
            'customer_id': payload.customer_id,
            'local_reference_id': payload.local_reference_id,
            'provider_name': self.PROVIDER_NAME,
            'provider_invoice_id': None,
            'invoice_number': None,
            'scenario': payload.scenario,
            'issue_date': payload.issue_date.isoformat(),
            'receiver_vkn_tckn': payload.receiver.vkn_tckn,
            'receiver_alias': payload.receiver.alias,
            'status': EInvoiceStatus.DRAFT.value,
            'provider_status_code': None,
            'provider_status_message': None,
            'ubl_xml': ubl_xml,
            'raw_create_response': None,
            'raw_status_response': None,
            'status_check_attempts': 0,
            'next_status_check_at': None,
            'created_at': now,
            'updated_at': now,
        }

    async def create_and_send(self, payload: EInvoiceCreateRequest) -> EInvoiceCreateResult:
        await self.repository.ensure_indexes()
        existing = await self.repository.find_by_local_reference_id(payload.local_reference_id)
        if existing:
            raise ValueError('local_reference_id already exists')

        try:
            ubl_xml = self.ubl_builder.build(payload)
        except UBLGenerationError as exc:
            raise ValueError(f'UBL generation failed: {exc}') from exc

        invoice_doc = self._build_invoice_document(payload, ubl_xml)
        await self.repository.create_invoice(invoice_doc)

        try:
            provider_result = await self.provider.createInvoiceFromUbl(ubl_xml, {
                'local_reference_id': payload.local_reference_id,
                'receiver_vkn_tckn': payload.receiver.vkn_tckn,
                'receiver_alias': payload.receiver.alias,
            })
            normalized_status = provider_result['normalized_status']
            await self.repository.update_invoice(invoice_doc['id'], {
                'provider_invoice_id': provider_result['provider_invoice_id'],
                'invoice_number': provider_result.get('invoice_number'),
                'provider_status_code': provider_result['provider_status_code'],
                'provider_status_message': provider_result['provider_status_message'],
                'raw_create_response': provider_result['payload'],
                'status': normalized_status,
                'status_check_attempts': 0,
                'next_status_check_at': (datetime.now(timezone.utc) + timedelta(seconds=self.provider.next_poll_delay_seconds(0))).isoformat(),
            })
            await self.repository.insert_provider_log({
                'id': str(uuid.uuid4()),
                'invoice_id': invoice_doc['id'],
                'action': 'create',
                'request_payload': {
                    'local_reference_id': payload.local_reference_id,
                    'receiver_vkn_tckn': payload.receiver.vkn_tckn,
                    'receiver_alias': payload.receiver.alias,
                    'xml_length': len(ubl_xml),
                },
                'response_payload': provider_result['payload'],
                'http_status': provider_result['http_status'],
                'created_at': now_iso(),
            })
        except ProviderError as exc:
            final_status = EInvoiceStatus.FAILED.value
            await self.repository.update_invoice(invoice_doc['id'], {
                'status': final_status,
                'provider_status_code': exc.provider_code,
                'provider_status_message': exc.provider_message,
                'raw_create_response': exc.raw_payload or {'error': exc.message, 'provider_code': exc.provider_code},
            })
            await self.repository.insert_provider_log({
                'id': str(uuid.uuid4()),
                'invoice_id': invoice_doc['id'],
                'action': 'create',
                'request_payload': {
                    'local_reference_id': payload.local_reference_id,
                    'receiver_vkn_tckn': payload.receiver.vkn_tckn,
                    'receiver_alias': payload.receiver.alias,
                    'xml_length': len(ubl_xml),
                },
                'response_payload': exc.raw_payload or {'error': exc.message, 'provider_code': exc.provider_code, 'provider_message': exc.provider_message},
                'http_status': exc.status_code,
                'created_at': now_iso(),
            })
            raise

        updated = await self.repository.get_invoice(invoice_doc['id'])
        return EInvoiceCreateResult(
            invoice_id=updated['id'],
            local_reference_id=updated['local_reference_id'],
            status=updated['status'],
            provider_name=updated['provider_name'],
            provider_invoice_id=updated.get('provider_invoice_id'),
            invoice_number=updated.get('invoice_number'),
            provider_status_code=updated.get('provider_status_code'),
            provider_status_message=updated.get('provider_status_message'),
        )

    async def create_test_smoke_invoice(self) -> EInvoiceCreateResult:
        payload = EInvoiceCreateRequest(
            local_reference_id=f"INV-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            issue_date=datetime.now(timezone.utc).date(),
            receiver={
                'vkn_tckn': self.TEST_RECEIVER_VKN_TCKN,
                'alias': self.TEST_RECEIVER_ALIAS,
                'title': 'TEST ALICI',
            },
            lines=[{
                'name': '2000 ml Ayran',
                'quantity': Decimal('10'),
                'unit_code': 'NIU',
                'unit_price': Decimal('45.00'),
                'vat_rate': Decimal('10'),
            }],
        )
        return await self.create_and_send(payload)

    async def get_invoice(self, invoice_id: str):
        return await self.repository.get_invoice(invoice_id)

    async def refresh_status(self, invoice_id: str) -> EInvoiceStatusResult:
        invoice = await self.repository.get_invoice(invoice_id)
        if not invoice:
            raise ValueError('invoice not found')
        provider_invoice_id = invoice.get('provider_invoice_id')
        if not provider_invoice_id:
            raise ValueError('provider_invoice_id missing')

        try:
            provider_result = await self.provider.getInvoiceStatus(provider_invoice_id)
        except ProviderError as exc:
            await self.repository.insert_provider_log({
                'id': str(uuid.uuid4()),
                'invoice_id': invoice_id,
                'action': 'status',
                'request_payload': {'provider_invoice_id': provider_invoice_id},
                'response_payload': exc.raw_payload or {'error': exc.message, 'provider_code': exc.provider_code, 'provider_message': exc.provider_message},
                'http_status': exc.status_code,
                'created_at': now_iso(),
            })
            raise

        next_attempt = (invoice.get('status_check_attempts') or 0) + 1
        normalized_status = provider_result['normalized_status']
        updates = {
            'provider_invoice_id': provider_result.get('provider_invoice_id') or provider_invoice_id,
            'invoice_number': provider_result.get('invoice_number') or invoice.get('invoice_number'),
            'provider_status_code': provider_result['provider_status_code'],
            'provider_status_message': provider_result['provider_status_message'],
            'raw_status_response': provider_result['payload'],
            'status': normalized_status,
            'status_check_attempts': next_attempt,
            'next_status_check_at': (datetime.now(timezone.utc) + timedelta(seconds=self.provider.next_poll_delay_seconds(next_attempt))).isoformat(),
        }
        if normalized_status in {EInvoiceStatus.SENT.value, EInvoiceStatus.FAILED.value}:
            updates['next_status_check_at'] = None
        updated = await self.repository.update_invoice(invoice_id, updates)
        await self.repository.insert_provider_log({
            'id': str(uuid.uuid4()),
            'invoice_id': invoice_id,
            'action': 'status',
            'request_payload': {'provider_invoice_id': provider_invoice_id},
            'response_payload': provider_result['payload'],
            'http_status': provider_result['http_status'],
            'created_at': now_iso(),
        })
        return EInvoiceStatusResult(
            invoice_id=invoice_id,
            status=updated['status'],
            provider_invoice_id=updated.get('provider_invoice_id'),
            provider_status_code=updated.get('provider_status_code'),
            provider_status_message=updated.get('provider_status_message'),
        )

    async def get_local_status(self, invoice_id: str):
        invoice = await self.repository.get_invoice(invoice_id)
        if not invoice:
            raise ValueError('invoice not found')
        return EInvoiceStatusResult(
            invoice_id=invoice_id,
            status=invoice['status'],
            provider_invoice_id=invoice.get('provider_invoice_id'),
            provider_status_code=invoice.get('provider_status_code'),
            provider_status_message=invoice.get('provider_status_message'),
        )
