from urllib.parse import urljoin
import asyncio
import re

import httpx
from bs4 import BeautifulSoup

from services.gib_import.errors import GibPortalError

LOGIN_URL = 'https://earsivportal.efatura.gov.tr/intragiris.html'
BASE_URL = 'https://earsivportal.efatura.gov.tr/'


class GibClient:
    INVALID_CREDENTIAL_MARKERS = [
        'kullanıcı kodu veya şifre hatalı',
        'kullanici kodu veya sifre hatali',
        'girdiğiniz bilgiler hatalı',
        'girdiginiz bilgiler hatali',
        'şifre hatalı',
        'sifre hatali',
        'hatalı giriş',
        'hatali giris',
        'geçersiz kullanıcı',
        'gecersiz kullanici',
        'yanlış şifre',
        'yanlis sifre',
        'invalid credentials',
    ]
    OTP_MARKERS = ['otp', 'tek kullanımlık', 'tek kullanimlik', 'doğrulama kodu', 'dogrulama kodu']
    CAPTCHA_MARKERS = ['captcha', 'güvenlik kodu', 'guvenlik kodu']
    AUTH_SUCCESS_MARKERS = ['çıkış', 'cikis', 'logout', 'fatura', 'earsiv', 'belge']

    def __init__(self, timeout=20.0, verify=True):
        self.timeout = timeout
        self.verify = verify

    async def _request_with_backoff(self, method: str, url: str, *, data=None, cookies=None, headers=None):
        last_error = None
        for attempt in range(5):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, verify=self.verify, follow_redirects=True) as client:
                    response = await client.request(method, url, data=data, cookies=cookies, headers=headers)
                    if response.status_code in {403, 429, 503}:
                        raise GibPortalError('gib_temporarily_unavailable', f'Portal temporarily unavailable: {response.status_code}', 503)
                    return response
            except GibPortalError as exc:
                last_error = exc
            except httpx.TimeoutException:
                last_error = GibPortalError('gib_temporarily_unavailable', 'Portal request timeout', 504)
            except httpx.HTTPError as exc:
                last_error = GibPortalError('gib_temporarily_unavailable', str(exc), 503)
            await asyncio.sleep(min(2 ** attempt, 16))
        if last_error:
            raise last_error
        raise GibPortalError('gib_temporarily_unavailable', 'Portal request failed', 503)

    async def fetch_login_page(self):
        response = await self._request_with_backoff('GET', LOGIN_URL)
        return response.text

    def _build_login_payload(self, html: str, username: str, password: str):
        soup = BeautifulSoup(html, 'html.parser')
        form = soup.find('form')
        if not form:
            raise GibPortalError('portal_layout_changed', 'Login form not found', 502)

        payload = {}
        for input_el in form.find_all('input'):
            name = input_el.get('name') or input_el.get('id')
            value = input_el.get('value', '')
            input_type = (input_el.get('type') or 'text').lower()
            if not name:
                continue
            if input_type == 'hidden':
                payload[name] = value

        inputs = [((el.get('name') or el.get('id') or ''), (el.get('type') or 'text').lower()) for el in form.find_all('input')]
        username_candidates = ['userid', 'username', 'userCode', 'kullanici', 'kullaniciKodu', 'txtUserName']
        password_candidates = ['password', 'sifre', 'parola', 'txtPassword']

        username_field = next((name for name, field_type in inputs if name in username_candidates or ('user' in name.lower() and field_type != 'password')), None)
        password_field = next((name for name, field_type in inputs if name in password_candidates or field_type == 'password'), None)
        if not username_field or not password_field:
            raise GibPortalError('portal_layout_changed', 'Login input fields not found', 502)

        payload[username_field] = username
        payload[password_field] = password
        action = form.get('action') or LOGIN_URL
        return urljoin(LOGIN_URL, action), payload

    def _classify_login_failure(self, html: str, status_code: int | None = None, response_url: str | None = None):
        soup = BeautifulSoup(html, 'html.parser')
        lower = html.lower()
        form = soup.find('form')
        password_input = soup.find('input', attrs={'type': lambda v: (v or '').lower() == 'password'})
        login_page_present = bool(form and password_input) or 'intragiris' in lower or (response_url or '').endswith('intragiris.html')
        success_marker_present = any(marker in lower for marker in self.AUTH_SUCCESS_MARKERS)
        invalid_marker_present = any(marker in lower for marker in self.INVALID_CREDENTIAL_MARKERS)
        otp_marker_present = any(marker in lower for marker in self.OTP_MARKERS)
        captcha_marker_present = any(marker in lower for marker in self.CAPTCHA_MARKERS)

        if captcha_marker_present:
            raise GibPortalError('captcha_required', 'Portal requires captcha', 403)
        if otp_marker_present:
            raise GibPortalError('otp_required', 'Portal requires OTP', 403)
        if login_page_present and invalid_marker_present and not success_marker_present:
            raise GibPortalError('invalid_credentials', 'Invalid credentials', 401)

        return {
            'login_page_present': login_page_present,
            'success_marker_present': success_marker_present,
            'invalid_marker_present': invalid_marker_present,
            'status_code': status_code,
            'response_url': response_url,
        }

    async def login(self, username: str, password: str):
        login_html = await self.fetch_login_page()
        action_url, payload = self._build_login_payload(login_html, username, password)
        response = await self._request_with_backoff('POST', action_url, data=payload)
        clues = self._classify_login_failure(response.text, response.status_code, str(response.url))
        if not self._looks_authenticated(response.text):
            if clues.get('login_page_present') and clues.get('invalid_marker_present'):
                raise GibPortalError('invalid_credentials', 'Invalid credentials', 401)
            raise GibPortalError('portal_layout_changed', 'Portal login result could not be classified safely', 502)
        return dict(response.cookies)

    def _looks_authenticated(self, html: str):
        lower = html.lower()
        if 'intragiris' in lower and 'password' in lower and ('şifre' in lower or 'sifre' in lower):
            return False
        return any(marker in lower for marker in self.AUTH_SUCCESS_MARKERS)

    async def verify_session(self, cookies: dict):
        response = await self._request_with_backoff('GET', BASE_URL, cookies=cookies)
        if not self._looks_authenticated(response.text):
            raise GibPortalError('session_expired', 'Portal session expired', 401)
        return True

    async def fetch_invoice_listing(self, cookies: dict, date_from: str, date_to: str):
        # Best-effort HTTP-first implementation; can be overridden via tests if portal requires a more specific endpoint.
        response = await self._request_with_backoff('GET', BASE_URL, cookies=cookies)
        return response.text

    def extract_invoice_refs(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        refs = []
        for node in soup.find_all(attrs={'data-invoice-url': True}):
            refs.append(urljoin(BASE_URL, node.get('data-invoice-url')))
        for node in soup.find_all('a', attrs={'data-detail-url': True}):
            refs.append(urljoin(BASE_URL, node.get('data-detail-url')))
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(' ', strip=True).lower()
            if any(token in href.lower() for token in ['fatura', 'invoice', 'detail']) or any(token in text for token in ['fatura', 'invoice', 'detay']):
                refs.append(urljoin(BASE_URL, href))
        deduped = []
        seen = set()
        for ref in refs:
            if ref not in seen:
                seen.add(ref)
                deduped.append(ref)
        return deduped

    def extract_next_page_url(self, html: str):
        soup = BeautifulSoup(html, 'html.parser')
        for link in soup.find_all('a', href=True):
            text = link.get_text(' ', strip=True).lower()
            href = link['href']
            if 'next' in text or 'sonraki' in text:
                return urljoin(BASE_URL, href)
        return None

    async def fetch_invoice_detail(self, cookies: dict, detail_url: str):
        response = await self._request_with_backoff('GET', detail_url, cookies=cookies)
        return response.text
