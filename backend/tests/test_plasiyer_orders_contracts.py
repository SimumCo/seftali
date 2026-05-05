import os
import uuid
from datetime import datetime, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
CFG = dotenv_values('/app/backend/.env')
CLIENT = MongoClient(CFG['MONGO_URL'])
DB = CLIENT[CFG['DB_NAME']]
CUSTOMER_ID = '8a422e18-791f-4e6a-88b0-583f20fba6d4'
PRODUCT_ID = 'AILEM_AYRAN_2L_TEST'


class TestPlasiyerOrdersContracts:
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

    def _create_temp_order(self, status='submitted'):
        order_id = str(uuid.uuid4())
        now_iso = datetime.now(timezone.utc).isoformat()
        DB['sf_orders'].insert_one({
            'id': order_id,
            'customer_id': CUSTOMER_ID,
            'status': status,
            'items': [{'product_id': PRODUCT_ID, 'qty': 5}],
            'created_at': now_iso,
            'updated_at': now_iso,
        })
        return order_id

    def test_list_orders_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/orders")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        assert isinstance(payload.get('data'), list)

    def test_request_edit_contract(self):
        order_id = self._create_temp_order(status='submitted')
        response = self.session.post(
            f"{BASE_URL}/api/seftali/sales/orders/{order_id}/request-edit",
            json={'note': 'contract-edit'},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        assert payload.get('data', {}).get('order_id') == order_id

    def test_approve_order_contract(self):
        order_id = self._create_temp_order(status='submitted')
        response = self.session.post(f"{BASE_URL}/api/seftali/sales/orders/{order_id}/approve")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        assert payload.get('data', {}).get('order_id') == order_id
