import sys

import pytest

sys.path.insert(0, '/app/backend')
from services.gib_import.errors import GibPortalError
from services.gib_import.import_service import GIBImportService
from services.gib_import.live_gib_adapter import LiveGibAdapter
from services.gib_import.mock_gib_adapter import MockGibAdapter
from services.gib_import.session_manager import session_manager

pytestmark = pytest.mark.asyncio


class TestLiveGibIntegration:
    def setup_method(self):
        session_manager._sessions.clear()

    async def test_login_success(self):
        class FakeClient:
            async def login(self, username, password):
                return {'sid': 'cookie-1'}
            async def verify_session(self, cookies):
                return True

        adapter = LiveGibAdapter(client=FakeClient())
        result = await adapter.connect('sales-1', 'testuser', 'secret')
        assert result['state'] == 'connected'
        assert result['username_masked']

    async def test_invalid_credentials(self):
        class FakeClient:
            async def login(self, username, password):
                raise GibPortalError('invalid_credentials', 'Invalid credentials', 401)

        adapter = LiveGibAdapter(client=FakeClient())
        with pytest.raises(GibPortalError) as exc:
            await adapter.connect('sales-1', 'bad', 'bad')
        assert exc.value.code == 'invalid_credentials'

    async def test_session_expired(self):
        class ConnectClient:
            async def login(self, username, password):
                return {'sid': 'cookie-1'}
            async def verify_session(self, cookies):
                return True

        class ExpireClient:
            async def verify_session(self, cookies):
                raise GibPortalError('session_expired', 'Portal session expired', 401)

        adapter = LiveGibAdapter(client=ConnectClient())
        await adapter.connect('sales-1', 'testuser', 'secret')
        adapter.client = ExpireClient()
        status = await adapter.status('sales-1')
        assert status['state'] == 'expired'
        assert status['last_error'] == 'session_expired'

    async def test_parser_integration_and_duplicate_protection(self):
        class FakeLiveAdapter:
            source = 'live_gib'
            async def fetch_payloads(self, salesperson_id, date_from, date_to):
                return [
                    {
                        'source_key': 'live-1',
                        'html_content': '''<html><body><div id="invoice-number">EA-LIVE-1</div><div id="invoice-date">2026-04-01</div><div id="invoice-ettn">LIVE-ETTN-1</div><div id="buyer-name">Live Test Market</div><div id="buyer-tax-no">4444444444</div><div id="grand-total">100.00</div><table id="invoice-lines"><tr data-line="1"><td class="product-code">LIVE1</td><td class="product-name">Live Product</td><td class="qty">10</td><td class="unit-price">10.00</td><td class="line-total">100.00</td></tr></table></body></html>'''
                    }
                ]

        service = GIBImportService(adapter_factory={'mock': MockGibAdapter, 'live': FakeLiveAdapter})
        first = await service.start_import('80ddfb6a-0bac-465b-a32f-0f119802661b', mode='live', date_from='2026-04-01', date_to='2026-04-18')
        second = await service.start_import('80ddfb6a-0bac-465b-a32f-0f119802661b', mode='live', date_from='2026-04-01', date_to='2026-04-18')
        assert first['invoice_count'] == 1
        assert second['invoice_count'] == 1

    async def test_mock_mode_regression(self):
        service = GIBImportService()

        class FakeRepo:
            async def create_import_job(self, salesperson_id):
                return {'id': 'job-1', 'created_at': '2026-04-18T00:00:00Z'}
            async def update_import_job(self, job_id, updates):
                return None
            async def upsert_invoice(self, invoice_doc, lookup_query):
                return {'document': {'id': 'inv-1', **invoice_doc}, 'created': True}
            async def upsert_product_catalog_entry(self, line):
                return line.get('product_id')
            async def replace_invoice_lines(self, invoice_id, lines):
                return None

        service.repository = FakeRepo()
        result = await service.start_import('80ddfb6a-0bac-465b-a32f-0f119802661b', mode='mock')
        assert result['status'] == 'completed'
        assert result['invoice_count'] >= 1

    async def test_live_mode_failure_handling(self):
        class FailingLiveAdapter:
            source = 'live_gib'
            async def fetch_payloads(self, salesperson_id, date_from, date_to):
                raise GibPortalError('portal_layout_changed', 'Portal layout changed', 502)

        service = GIBImportService(adapter_factory={'mock': MockGibAdapter, 'live': FailingLiveAdapter})

        class FakeRepo:
            async def create_import_job(self, salesperson_id):
                return {'id': 'job-2', 'created_at': '2026-04-18T00:00:00Z'}
            async def update_import_job(self, job_id, updates):
                return None

        service.repository = FakeRepo()
        with pytest.raises(GibPortalError) as exc:
            await service.start_import('80ddfb6a-0bac-465b-a32f-0f119802661b', mode='live', date_from='2026-04-01', date_to='2026-04-18')
        assert exc.value.code == 'portal_layout_changed'
