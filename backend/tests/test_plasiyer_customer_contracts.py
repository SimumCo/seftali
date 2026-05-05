import os

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
AILEM_CUSTOMER_ID = '8a422e18-791f-4e6a-88b0-583f20fba6d4'


class TestPlasiyerCustomerContracts:
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

    def test_list_customers_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/customers")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        assert isinstance(payload.get('data'), list)

    def test_customers_summary_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/customers/summary")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or []
        assert isinstance(data, list)
        if data:
            for key in ['id', 'pending_orders_count', 'total_orders', 'total_deliveries']:
                assert key in data[0]

    def test_customer_consumption_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/customers/{AILEM_CUSTOMER_ID}/consumption")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or {}
        for key in ['customer_id', 'customer_name', 'products', 'total_products']:
            assert key in data
