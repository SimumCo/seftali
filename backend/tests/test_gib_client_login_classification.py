import pytest
import sys

sys.path.insert(0, '/app/backend')
from services.gib_import.errors import GibPortalError
from services.gib_import.gib_client import GibClient


class DummyResponse:
    def __init__(self, text, status_code=200, url='https://earsivportal.efatura.gov.tr/intragiris.html', cookies=None):
        self.text = text
        self.status_code = status_code
        self.url = url
        self.cookies = cookies or {}


@pytest.mark.asyncio
async def test_invalid_credentials_detected_from_login_error_html(monkeypatch):
    client = GibClient()

    async def fake_fetch_login_page():
        return '<html><body><form action="/login"><input name="userid"><input type="password" name="password"></form></body></html>'

    async def fake_request(method, url, data=None, cookies=None, headers=None):
        return DummyResponse('<html><body><div class="alert">Kullanıcı kodu veya şifre hatalı</div><form action="/login"><input name="userid"><input type="password" name="password"></form></body></html>')

    monkeypatch.setattr(client, 'fetch_login_page', fake_fetch_login_page)
    monkeypatch.setattr(client, '_request_with_backoff', fake_request)

    with pytest.raises(GibPortalError) as exc:
        await client.login('bad', 'bad')
    assert exc.value.code == 'invalid_credentials'


@pytest.mark.asyncio
async def test_login_page_repeat_without_error_becomes_portal_layout_changed(monkeypatch):
    client = GibClient()

    async def fake_fetch_login_page():
        return '<html><body><form action="/login"><input name="userid"><input type="password" name="password"></form></body></html>'

    async def fake_request(method, url, data=None, cookies=None, headers=None):
        return DummyResponse('<html><body><form action="/login"><input name="userid"><input type="password" name="password"></form></body></html>')

    monkeypatch.setattr(client, 'fetch_login_page', fake_fetch_login_page)
    monkeypatch.setattr(client, '_request_with_backoff', fake_request)

    with pytest.raises(GibPortalError) as exc:
        await client.login('bad', 'bad')
    assert exc.value.code == 'portal_layout_changed'
