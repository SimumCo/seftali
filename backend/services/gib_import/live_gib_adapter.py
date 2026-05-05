from services.gib_import.errors import GibPortalError
from services.gib_import.gib_client import GibClient
from services.gib_import.session_manager import session_manager


class LiveGibAdapter:
    source = 'live_gib'

    def __init__(self, client=None):
        self.client = client or GibClient()

    async def connect(self, salesperson_id: str, username: str, password: str):
        cookies = await self.client.login(username, password)
        await self.client.verify_session(cookies)
        return session_manager.connect(salesperson_id, username, cookies)

    async def status(self, salesperson_id: str):
        current = session_manager.get(salesperson_id)
        if not current:
            return {'state': 'not_connected'}
        if current.get('state') == 'expired':
            return {'state': 'expired', 'username_masked': current.get('username_masked'), 'last_error': current.get('last_error')}
        try:
            await self.client.verify_session(current['cookies'])
            current['last_verified_at'] = session_manager._now_iso()
            return {'state': 'connected', 'username_masked': current.get('username_masked'), 'last_verified_at': current.get('last_verified_at')}
        except GibPortalError as exc:
            session_manager.mark_expired(salesperson_id, exc.code)
            return {'state': 'expired', 'username_masked': current.get('username_masked'), 'last_error': exc.code}

    async def disconnect(self, salesperson_id: str):
        return session_manager.disconnect(salesperson_id)

    async def fetch_payloads(self, salesperson_id: str, date_from: str, date_to: str):
        current = session_manager.get(salesperson_id)
        if not current:
            raise GibPortalError('not_connected', 'No active GİB session', 409)
        if current.get('state') == 'expired':
            raise GibPortalError('session_expired', 'Portal session expired', 401)

        cookies = current['cookies']
        await self.client.verify_session(cookies)
        listing_html = await self.client.fetch_invoice_listing(cookies, date_from, date_to)
        refs = self.client.extract_invoice_refs(listing_html)
        if not refs:
            # if portal returns a page that is already a detail HTML, reuse it as a single payload
            return [{
                'source_key': f'live-inline-{salesperson_id}',
                'html_content': listing_html,
            }]

        payloads = []
        next_page_url = self.client.extract_next_page_url(listing_html)
        page_count = 0
        while True:
            for index, ref in enumerate(refs, start=1):
                html_content = await self.client.fetch_invoice_detail(cookies, ref)
                payloads.append({
                    'source_key': f'live-{page_count + 1}-{index}',
                    'html_content': html_content,
                    'detail_url': ref,
                })
            if not next_page_url or page_count >= 9:
                break
            page_count += 1
            listing_html = await self.client.fetch_invoice_detail(cookies, next_page_url)
            refs = self.client.extract_invoice_refs(listing_html)
            next_page_url = self.client.extract_next_page_url(listing_html)
        return payloads
