import os

import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')


class TestPlasiyerCampaignsContracts:
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

    def test_list_campaigns_contract(self):
        response = self.session.get(f"{BASE_URL}/api/seftali/sales/campaigns")
        assert response.status_code == 200
        payload = response.json()
        assert payload.get('success') is True
        data = payload.get('data') or []
        assert isinstance(data, list)
        if data:
            for key in ['id', 'title', 'status']:
                assert key in data[0]
