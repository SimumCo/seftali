import os

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestSmartOrderRouteContracts:
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

    def test_get_warehouse_draft_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or {}
        for key in ['route_day', 'customer_count', 'order_customer_count', 'draft_customer_count', 'order_items', 'total_order_qty']:
            assert key in data

    def test_get_smart_orders_alias_contract(self):
        legacy_response = self.session.get(f"{BASE_URL}/api/seftali/sales/warehouse-draft")
        canonical_response = self.session.get(f"{BASE_URL}/api/seftali/sales/smart-orders")
        assert legacy_response.status_code == 200
        assert canonical_response.status_code == 200
        assert legacy_response.json() == canonical_response.json()

    def test_submit_smart_orders_alias_contract(self):
        response = self.session.post(
            f"{BASE_URL}/api/seftali/sales/smart-orders/submit",
            json={"note": "canonical-contract-test"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or {}
        for key in ['id', 'type', 'route_day', 'submitted_by', 'status', 'items']:
            assert key in data

    def test_submit_warehouse_draft_contract(self):
        response = self.session.post(
            f"{BASE_URL}/api/seftali/sales/warehouse-draft/submit",
            json={"note": "contract-test"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or {}
        for key in ['id', 'type', 'route_day', 'submitted_by', 'status', 'items']:
            assert key in data

    def test_plasiyer_order_calculation_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/plasiyer/order-calculation", params={"route_day": "MON"})
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or {}
        for key in ['salesperson_id', 'route_day', 'customers', 'totals', 'summary']:
            assert key in data

    def test_route_order_by_day_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/route-order/MON")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or {}
        for key in ['salesperson_id', 'route_day', 'customers', 'totals', 'summary']:
            assert key in data

    def test_route_order_tomorrow_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/route-order")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or {}
        for key in ['salesperson_id', 'route_day', 'customers', 'totals', 'summary']:
            assert key in data
