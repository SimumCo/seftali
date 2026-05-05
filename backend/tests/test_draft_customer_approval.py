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
SALESPERSON_ID = '80ddfb6a-0bac-465b-a32f-0f119802661b'


class TestDraftCustomerApproval:
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

    def _create_draft(self, **overrides):
        draft_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        identity_value = overrides.get('identity_number')
        tax_number = overrides.get('tax_number', f"9{draft_id.replace('-', '')[:9]}")
        tc_no = overrides.get('tc_no')
        if identity_value is None:
            identity_value = tc_no or tax_number

        if identity_value is not None:
            DB['draft_customers'].delete_many({'salesperson_id': SALESPERSON_ID, 'identity_number': identity_value})
        else:
            DB['draft_customers'].delete_many({'salesperson_id': SALESPERSON_ID, 'business_name': overrides.get('business_name', f'Test Draft {draft_id[:6]}')})

        payload = {
            'id': draft_id,
            'salesperson_id': SALESPERSON_ID,
            'business_name': overrides.get('business_name', f'Test Draft {draft_id[:6]}'),
            'tax_number': tax_number,
            'tc_no': tc_no,
            'identity_number': identity_value,
            'invoice_count': 2,
            'first_invoice_date': '2026-03-01',
            'last_invoice_date': '2026-03-10',
            'total_amount': 1500.0,
            'status': 'review_pending',
            'created_at': now,
            'updated_at': now,
        }
        DB['draft_customers'].insert_one(payload)
        return payload

    def test_approve_draft_customer_success(self):
        draft = self._create_draft(tax_number='5555555555', business_name='Approve Success Ltd')
        response = self.session.post(
            f"{BASE_URL}/api/draft-customers/{draft['id']}/approve",
            json={
                'customer_type': 'retail',
                'risk_limit': 10000,
                'balance': 0,
                'phone': '05000000000',
                'address': 'Istanbul',
            },
        )
        assert response.status_code == 200
        payload = response.json()
        data = payload.get('data') or {}
        assert data.get('customer_id')
        assert data.get('username') == '5555555555'
        assert data.get('must_change_password') is True

        customer = DB['customers'].find_one({'id': data['customer_id']}, {'_id': 0})
        user = DB['customer_users'].find_one({'username': '5555555555'}, {'_id': 0})
        updated_draft = DB['draft_customers'].find_one({'id': draft['id']}, {'_id': 0})

        assert customer is not None
        assert user is not None
        assert user['must_change_password'] is True
        assert user['password_hash'] != '123123'
        assert updated_draft['status'] == 'approved'

    def test_approve_reuses_existing_customer_and_user(self):
        draft = self._create_draft(tax_number='6666666666', business_name='Duplicate Draft Reuse')

        existing_customer_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        DB['customers'].delete_many({'identity_number': '6666666666'})
        DB['customer_users'].delete_many({'username': '6666666666'})
        DB['customers'].insert_one({
            'id': existing_customer_id,
            'salesperson_id': SALESPERSON_ID,
            'business_name': 'Existing Customer',
            'tax_no': '6666666666',
            'tc_no': None,
            'identity_number': '6666666666',
            'customer_type': 'retail',
            'risk_limit': 2000,
            'balance': 0,
            'phone': '05000000999',
            'address': 'Existing Address',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        })
        DB['customer_users'].insert_one({
            'id': str(uuid.uuid4()),
            'customer_id': existing_customer_id,
            'username': '6666666666',
            'password_hash': 'hashed-value',
            'must_change_password': True,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        })

        response = self.session.post(
            f"{BASE_URL}/api/draft-customers/{draft['id']}/approve",
            json={
                'customer_type': 'retail',
                'risk_limit': 5000,
                'balance': 100,
                'phone': '05000000002',
                'address': 'Izmir',
            },
        )
        assert response.status_code == 200
        data = response.json()['data']

        assert data['customer_id'] == existing_customer_id
        assert data['username'] == '6666666666'
        assert DB['customer_users'].count_documents({'username': '6666666666'}) == 1

    def test_approve_missing_identity_returns_error(self):
        draft = self._create_draft(tax_number=None, tc_no=None, identity_number=None, business_name='No Identity Draft')
        response = self.session.post(
            f"{BASE_URL}/api/draft-customers/{draft['id']}/approve",
            json={
                'customer_type': 'retail',
                'risk_limit': 10000,
                'balance': 0,
                'phone': '05000000003',
                'address': 'Bursa',
            },
        )
        assert response.status_code == 400
        payload = response.json()
        assert 'tc_no veya tax_number' in payload.get('detail', '')
