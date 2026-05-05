import os

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPlasiyerStockContracts:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

        login_response = self.session.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": "sf_plasiyer", "password": "plasiyer123"},
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        token = login_response.json().get('access_token')
        assert token, 'No access token received'
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def test_get_plasiyer_stock_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/stock")
        assert response.status_code == 200
        payload = response.json()
        assert 'success' in payload
        if payload.get('success'):
            data = payload.get('data') or {}
            for key in ['salesperson_id', 'items']:
                assert key in data

    def test_update_plasiyer_stock_contract(self):
        current_response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/stock")
        assert current_response.status_code == 200
        current_payload = current_response.json()
        assert current_payload.get('success') is True
        items = current_payload.get('data', {}).get('items', [])
        assert items, 'No stock items available for contract test'

        first_item = items[0]
        response = self.session.patch(
            f"{BASE_URL}/api/seftali/sales/plasiyer/stock",
            json={
                'operation': 'set',
                'items': [{'product_id': first_item['product_id'], 'qty': first_item['qty']}],
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or {}
        for key in ['success', 'items_updated']:
            assert key in data
