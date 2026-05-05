import os

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
PLASIYER_ID = '80ddfb6a-0bac-465b-a32f-0f119802661b'


class TestGibImportContracts:
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

    def test_start_gib_import_contract(self):
        response = self.session.post(f"{BASE_URL}/api/gib/import/start")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or {}
        assert 'job' in data
        assert 'draft_customers' in data
        assert 'job_id' in data['job']
        assert 'status' in data['job']

    def test_list_draft_customers_contract(self):
        self.session.post(f"{BASE_URL}/api/gib/import/start")
        response = self.session.get(f"{BASE_URL}/api/draft-customers", params={'salespersonId': PLASIYER_ID})
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or []
        assert isinstance(data, list)
        if data:
            for key in ['business_name', 'invoice_count', 'first_invoice_date', 'last_invoice_date', 'total_amount', 'status']:
                assert key in data[0]
