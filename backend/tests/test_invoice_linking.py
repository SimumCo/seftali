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
OTHER_SALESPERSON_ID = 'different-salesperson'


class TestInvoiceLinking:
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

    def _create_customer(self, identity_number, salesperson_id=SALESPERSON_ID, tax_no=None, tc_no=None):
        customer_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        if identity_number is not None:
            DB['customers'].delete_many({'identity_number': identity_number})
        else:
            DB['customers'].delete_many({'salesperson_id': salesperson_id, 'business_name': 'Missing Identity Customer'})

        payload = {
            'id': customer_id,
            'salesperson_id': salesperson_id,
            'business_name': f'Customer {identity_number}',
            'customer_type': 'retail',
            'risk_limit': 0,
            'balance': 0,
            'phone': '',
            'address': '',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        }
        if tax_no is not None:
            payload['tax_no'] = tax_no
        if tc_no is not None:
            payload['tc_no'] = tc_no
        if identity_number is not None:
            payload['identity_number'] = identity_number
        DB['customers'].insert_one(payload)
        return customer_id

    def _create_invoice(self, identity_number, salesperson_id=SALESPERSON_ID, customer_id=None, invoice_number=None, tc_no=None, tax_no=None, ettn=None):
        invoice_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        payload = {
            'id': invoice_id,
            'salesperson_id': salesperson_id,
            'customer_id': customer_id,
            'draft_customer_id': None,
            'invoice_number': invoice_number or f'INV-{uuid.uuid4()}',
            'invoice_date': '2026-03-01',
            'business_name': 'Linked Invoice Customer',
            'identity_number': identity_number,
            'currency': 'TRY',
            'grand_total': 100.0,
            'raw_ref': {'source': 'test'},
            'raw_payload': {},
            'status': 'imported',
            'is_cancelled': False,
            'created_at': now,
            'updated_at': now,
        }
        if ettn is not None:
            payload['ettn'] = ettn
        if tax_no is not None:
            payload['tax_no'] = tax_no
        if tc_no is not None:
            payload['tc_no'] = tc_no
        DB['invoices'].insert_one(payload)
        return invoice_id

    def test_links_three_invoices(self):
        identity = '9000000001'
        customer_id = self._create_customer(identity, tax_no=identity)
        DB['invoices'].delete_many({'identity_number': identity})
        for idx in range(3):
            self._create_invoice(identity, tax_no=identity, invoice_number=f'LINK3-{idx}')

        response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/link-invoices")
        assert response.status_code == 200
        data = response.json()['data']
        assert data['customer_id'] == customer_id
        assert data['linked_count'] == 3
        assert data['skipped_count'] == 0
        assert data['conflict_count'] == 0

    def test_idempotent_re_run(self):
        identity = '9000000002'
        customer_id = self._create_customer(identity, tax_no=identity)
        DB['invoices'].delete_many({'identity_number': identity})
        for idx in range(2):
            self._create_invoice(identity, tax_no=identity, invoice_number=f'IDEMP-{idx}')

        first = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/link-invoices")
        second = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/link-invoices")
        assert first.status_code == 200
        assert second.status_code == 200
        second_data = second.json()['data']
        assert second_data['linked_count'] == 0
        assert second_data['skipped_count'] == 2
        assert second_data['conflict_count'] == 0

    def test_conflict_invoice_ownership(self):
        identity = '9000000003'
        customer_id = self._create_customer(identity, tax_no=identity)
        other_customer_id = self._create_customer('9000000999', tax_no='9000000999')
        DB['invoices'].delete_many({'identity_number': identity})
        self._create_invoice(identity, tax_no=identity, invoice_number='CONF-1')
        self._create_invoice(identity, tax_no=identity, customer_id=other_customer_id, invoice_number='CONF-2')

        response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/link-invoices")
        assert response.status_code == 200
        data = response.json()['data']
        assert data['linked_count'] == 1
        assert data['conflict_count'] == 1

    def test_links_with_tax_number_when_tc_missing(self):
        identity = '9000000004'
        customer_id = self._create_customer(identity, tax_no=identity, tc_no=None)
        DB['invoices'].delete_many({'identity_number': identity})
        self._create_invoice(identity, tax_no=identity, tc_no=None, invoice_number='TAXONLY-1')

        response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/link-invoices")
        assert response.status_code == 200
        data = response.json()['data']
        assert data['linked_count'] == 1
        assert data['conflict_count'] == 0

    def test_customer_identity_missing_returns_error(self):
        customer_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        DB['customers'].delete_many({
            'salesperson_id': SALESPERSON_ID,
            '$or': [
                {'identity_number': None},
                {'identity_number': {'$exists': False}},
            ],
        })
        DB['customers'].insert_one({
            'id': customer_id,
            'salesperson_id': SALESPERSON_ID,
            'business_name': 'Missing Identity Customer',
            'customer_type': 'retail',
            'risk_limit': 0,
            'balance': 0,
            'phone': '',
            'address': '',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        })
        response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/link-invoices")
        assert response.status_code == 400
        assert 'Customer identity missing' in response.json().get('detail', '')
