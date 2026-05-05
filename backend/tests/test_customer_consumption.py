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


class TestCustomerConsumption:
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

    def _seed_customer(self, identity_number: str):
        customer_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        DB['customers'].delete_many({'identity_number': identity_number})
        DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        DB['customers'].insert_one({
            'id': customer_id,
            'salesperson_id': SALESPERSON_ID,
            'business_name': f'Consumption {identity_number}',
            'tax_no': identity_number,
            'tc_no': None,
            'identity_number': identity_number,
            'customer_type': 'retail',
            'risk_limit': 0,
            'balance': 0,
            'phone': '',
            'address': '',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        })
        return customer_id

    def _seed_product(self, product_id: str, name: str):
        DB['products'].delete_many({'product_id': product_id})
        DB['products'].insert_one({
            'product_id': product_id,
            'name': name,
            'normalized_name': name.lower(),
            'unit_type': 'adet',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        })

    def _seed_alias(self, alias: str, product_id: str):
        normalized = alias.strip().lower()
        DB['product_aliases'].delete_many({'normalized_alias': normalized})
        DB['product_aliases'].insert_one({
            'id': str(uuid.uuid4()),
            'product_id': product_id,
            'alias': alias,
            'normalized_alias': normalized,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        })

    def _seed_invoice(self, customer_id: str, identity_number: str, invoice_date: str, *, is_cancelled=False, lines=None):
        invoice_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        DB['invoices'].insert_one({
            'id': invoice_id,
            'salesperson_id': SALESPERSON_ID,
            'customer_id': customer_id,
            'invoice_number': f'CONS-{uuid.uuid4()}',
            'invoice_date': invoice_date,
            'business_name': 'Consumption Customer',
            'tax_no': identity_number,
            'identity_number': identity_number,
            'currency': 'TRY',
            'grand_total': 100.0,
            'raw_ref': {'source': 'test'},
            'raw_payload': {},
            'status': 'imported',
            'is_cancelled': is_cancelled,
            'created_at': now,
            'updated_at': now,
        })
        DB['invoice_lines'].delete_many({'invoice_id': invoice_id})
        line_docs = []
        for idx, line in enumerate(lines or [], start=1):
            line_docs.append({
                'id': str(uuid.uuid4()),
                'invoice_id': invoice_id,
                'line_no': idx,
                'product_id': line.get('product_id'),
                'product_code': line.get('product_code'),
                'product_name': line['product_name'],
                'normalized_name': line['product_name'].strip().lower(),
                'quantity': line['quantity'],
                'unit_price': 1.0,
                'line_total': line['quantity'],
                'created_at': now,
                'updated_at': now,
            })
        if line_docs:
            DB['invoice_lines'].insert_many(line_docs)
        return invoice_id

    def test_three_invoices_calculate_daily_consumption(self):
        customer_id = self._seed_customer('9100000001')
        self._seed_product('AYRAN_2L_TEST', 'Ayran 2L')
        DB['invoice_lines'].delete_many({})
        DB['invoices'].delete_many({'customer_id': customer_id})
        DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        self._seed_invoice(customer_id, '9100000001', '2026-04-01', lines=[{'product_id': 'AYRAN_2L_TEST', 'product_name': 'Ayran 2L', 'quantity': 400}])
        self._seed_invoice(customer_id, '9100000001', '2026-04-05', lines=[{'product_id': 'AYRAN_2L_TEST', 'product_name': 'Ayran 2L', 'quantity': 300}])
        self._seed_invoice(customer_id, '9100000001', '2026-04-08', lines=[{'product_id': 'AYRAN_2L_TEST', 'product_name': 'Ayran 2L', 'quantity': 300}])

        response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        assert response.status_code == 200
        data = response.json()['data']
        assert data['processed_product_count'] == 1
        record = DB['customer_product_consumptions'].find_one({'customer_id': customer_id, 'product_id': 'AYRAN_2L_TEST'}, {'_id': 0})
        assert round(record['daily_consumption'], 2) == 100.0

        get_response = self.session.get(f"{BASE_URL}/api/customers/{customer_id}/consumption")
        assert get_response.status_code == 200
        list_data = get_response.json()['data']
        assert isinstance(list_data, list)
        assert list_data[0]['product_id'] == 'AYRAN_2L_TEST'

    def test_single_invoice_returns_safe_null_consumption(self):
        customer_id = self._seed_customer('9100000002')
        self._seed_product('YOGURT_TEST', 'Yoğurt')
        DB['invoice_lines'].delete_many({})
        DB['invoices'].delete_many({'customer_id': customer_id})
        DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        self._seed_invoice(customer_id, '9100000002', '2026-04-01', lines=[{'product_id': 'YOGURT_TEST', 'product_name': 'Yoğurt', 'quantity': 10}])

        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        record = DB['customer_product_consumptions'].find_one({'customer_id': customer_id, 'product_id': 'YOGURT_TEST'}, {'_id': 0})
        assert record['daily_consumption'] is None

    def test_zero_day_diff_is_skipped(self):
        customer_id = self._seed_customer('9100000003')
        self._seed_product('SUT_TEST', 'Süt')
        DB['invoice_lines'].delete_many({})
        DB['invoices'].delete_many({'customer_id': customer_id})
        DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        DB['customer_product_daily_consumptions'].delete_many({'customer_id': customer_id})
        self._seed_invoice(customer_id, '9100000003', '2026-04-01', lines=[{'product_id': 'SUT_TEST', 'product_name': 'Süt', 'quantity': 20}])
        self._seed_invoice(customer_id, '9100000003', '2026-04-01', lines=[{'product_id': 'SUT_TEST', 'product_name': 'Süt', 'quantity': 15}])

        response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        assert response.status_code == 200
        record = DB['customer_product_consumptions'].find_one({'customer_id': customer_id, 'product_id': 'SUT_TEST'}, {'_id': 0})
        assert record['daily_consumption'] is None
        assert DB['customer_product_daily_consumptions'].count_documents({'customer_id': customer_id, 'product_id': 'SUT_TEST'}) == 0

    def test_alias_product_match_works(self):
        customer_id = self._seed_customer('9100000004')
        self._seed_product('AYRAN_ALIAS_TEST', 'Ayran 2L')
        self._seed_alias('Ayran 2L Büyük', 'AYRAN_ALIAS_TEST')
        DB['invoice_lines'].delete_many({})
        DB['invoices'].delete_many({'customer_id': customer_id})
        DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        self._seed_invoice(customer_id, '9100000004', '2026-04-01', lines=[{'product_name': 'Ayran 2L Büyük', 'quantity': 30}])
        self._seed_invoice(customer_id, '9100000004', '2026-04-04', lines=[{'product_name': 'Ayran 2L Büyük', 'quantity': 30}])

        response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        assert response.status_code == 200
        record = DB['customer_product_consumptions'].find_one({'customer_id': customer_id, 'product_id': 'AYRAN_ALIAS_TEST'}, {'_id': 0})
        assert record is not None

    def test_recalculate_is_idempotent(self):
        customer_id = self._seed_customer('9100000005')
        self._seed_product('PEYNIR_TEST', 'Peynir')
        DB['invoice_lines'].delete_many({})
        DB['invoices'].delete_many({'customer_id': customer_id})
        DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        self._seed_invoice(customer_id, '9100000005', '2026-04-01', lines=[{'product_id': 'PEYNIR_TEST', 'product_name': 'Peynir', 'quantity': 12}])
        self._seed_invoice(customer_id, '9100000005', '2026-04-05', lines=[{'product_id': 'PEYNIR_TEST', 'product_name': 'Peynir', 'quantity': 8}])

        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        assert DB['customer_product_consumptions'].count_documents({'customer_id': customer_id, 'product_id': 'PEYNIR_TEST'}) == 1

    def test_cancelled_invoice_is_ignored(self):
        customer_id = self._seed_customer('9100000006')
        self._seed_product('AYRAN_CANCEL_TEST', 'Ayran İptal')
        DB['invoice_lines'].delete_many({})
        DB['invoices'].delete_many({'customer_id': customer_id})
        DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        self._seed_invoice(customer_id, '9100000006', '2026-04-01', is_cancelled=True, lines=[{'product_id': 'AYRAN_CANCEL_TEST', 'product_name': 'Ayran İptal', 'quantity': 50}])
        self._seed_invoice(customer_id, '9100000006', '2026-04-05', lines=[{'product_id': 'AYRAN_CANCEL_TEST', 'product_name': 'Ayran İptal', 'quantity': 50}])

        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        record = DB['customer_product_consumptions'].find_one({'customer_id': customer_id, 'product_id': 'AYRAN_CANCEL_TEST'}, {'_id': 0})
        assert record['daily_consumption'] is None
