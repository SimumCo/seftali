import os
import uuid
from datetime import datetime, timezone

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
CUSTOMER_ID = '8a422e18-791f-4e6a-88b0-583f20fba6d4'
PRODUCT_ID = 'AILEM_AYRAN_2L_TEST'


class TestPlasiyerDeliveriesContracts:
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

    def test_list_deliveries_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/deliveries")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        assert isinstance(payload.get('data'), list)

    def test_create_delivery_contract(self):
        invoice_no = f"SMOKE-{uuid.uuid4()}"
        response = self.session.post(
            f"{BASE_URL}/api/seftali/sales/deliveries",
            json={
                'customer_id': CUSTOMER_ID,
                'delivery_type': 'route',
                'invoice_no': invoice_no,
                'items': [{'product_id': PRODUCT_ID, 'qty': 1}],
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or {}
        for key in ['id', 'customer_id', 'delivery_type', 'acceptance_status', 'items']:
            assert key in data
