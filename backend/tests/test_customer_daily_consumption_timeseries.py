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


class TestCustomerDailyConsumptionTimeseries:
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
        assert token
        self.session.headers.update({"Authorization": f"Bearer {token}"})

    def _seed_customer(self, identity_number: str):
        customer_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self._cleanup_identity(identity_number)
        DB['customers'].insert_one({
            'id': customer_id,
            'salesperson_id': SALESPERSON_ID,
            'business_name': f'Daily Series {identity_number}',
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

    def _cleanup_identity(self, identity_number: str):
        invoices = list(DB['invoices'].find({'identity_number': identity_number}, {'_id': 0, 'id': 1, 'customer_id': 1}))
        invoice_ids = [invoice['id'] for invoice in invoices]
        customer_ids = list({invoice.get('customer_id') for invoice in invoices if invoice.get('customer_id')})
        DB['invoice_lines'].delete_many({'invoice_id': {'$in': invoice_ids}})
        DB['invoices'].delete_many({'identity_number': identity_number})
        for customer_id in customer_ids:
            DB['customer_product_daily_consumptions'].delete_many({'customer_id': customer_id})
            DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        DB['customers'].delete_many({'identity_number': identity_number})

    def _seed_product(self, product_id: str, name: str):
        now = datetime.now(timezone.utc).isoformat()
        DB['products'].delete_many({'product_id': product_id})
        DB['products'].insert_one({
            'product_id': product_id,
            'name': name,
            'normalized_name': name.lower(),
            'unit_type': 'adet',
            'created_at': now,
            'updated_at': now,
        })

    def _seed_alias(self, alias: str, product_id: str):
        now = datetime.now(timezone.utc).isoformat()
        normalized = ' '.join(alias.lower().strip().split())
        DB['product_aliases'].delete_many({'normalized_alias': normalized})
        DB['product_aliases'].insert_one({
            'id': str(uuid.uuid4()),
            'product_id': product_id,
            'alias': alias,
            'normalized_alias': normalized,
            'created_at': now,
            'updated_at': now,
        })

    def _seed_invoice(self, customer_id: str, identity_number: str, invoice_date: str, *, is_cancelled=False, lines=None):
        invoice_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        DB['invoices'].insert_one({
            'id': invoice_id,
            'salesperson_id': SALESPERSON_ID,
            'customer_id': customer_id,
            'invoice_number': f'DAILY-{uuid.uuid4()}',
            'invoice_date': invoice_date,
            'business_name': 'Daily Series Customer',
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
        line_docs = []
        for idx, line in enumerate(lines or [], start=1):
            line_docs.append({
                'id': str(uuid.uuid4()),
                'invoice_id': invoice_id,
                'line_no': idx,
                'product_id': line.get('product_id'),
                'product_code': line.get('product_code'),
                'product_name': line['product_name'],
                'normalized_name': ' '.join(line['product_name'].lower().strip().split()),
                'quantity': line['quantity'],
                'unit_price': 1.0,
                'line_total': line['quantity'],
                'created_at': now,
                'updated_at': now,
            })
        if line_docs:
            DB['invoice_lines'].insert_many(line_docs)
        return invoice_id

    def test_two_invoices_generate_correct_daily_rows(self):
        customer_id = self._seed_customer('9200000001')
        self._seed_product('RATE_TEST_A', 'Rate Test A')
        self._seed_invoice(customer_id, '9200000001', '2026-01-01', lines=[{'product_id': 'RATE_TEST_A', 'product_name': 'Rate Test A', 'quantity': 100}])
        self._seed_invoice(customer_id, '9200000001', '2026-01-11', lines=[{'product_id': 'RATE_TEST_A', 'product_name': 'Rate Test A', 'quantity': 200}])

        response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        assert response.status_code == 200
        rows = list(DB['customer_product_daily_consumptions'].find({'customer_id': customer_id, 'product_id': 'RATE_TEST_A'}, {'_id': 0}).sort('date', 1))
        assert len(rows) == 10
        assert rows[0]['date'] == '2026-01-02'
        assert rows[-1]['date'] == '2026-01-11'
        assert all(row['daily_rate'] == 10 for row in rows)
        assert DB['customer_product_daily_consumptions'].count_documents({'customer_id': customer_id, 'product_id': 'RATE_TEST_A', 'date': '2026-01-01'}) == 0

    def test_same_day_merge_happens_before_interval_calculation(self):
        customer_id = self._seed_customer('9200000002')
        self._seed_product('RATE_TEST_B', 'Rate Test B')
        self._seed_invoice(customer_id, '9200000002', '2026-01-01', lines=[{'product_id': 'RATE_TEST_B', 'product_name': 'Rate Test B', 'quantity': 60}])
        self._seed_invoice(customer_id, '9200000002', '2026-01-01', lines=[{'product_id': 'RATE_TEST_B', 'product_name': 'Rate Test B', 'quantity': 40}])
        self._seed_invoice(customer_id, '9200000002', '2026-01-11', lines=[{'product_id': 'RATE_TEST_B', 'product_name': 'Rate Test B', 'quantity': 200}])

        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        rows = list(DB['customer_product_daily_consumptions'].find({'customer_id': customer_id, 'product_id': 'RATE_TEST_B'}, {'_id': 0}))
        assert len(rows) == 10
        assert all(row['daily_rate'] == 10 for row in rows)

    def test_recalculate_rebuilds_daily_series_without_duplicates(self):
        customer_id = self._seed_customer('9200000003')
        self._seed_product('RATE_TEST_C', 'Rate Test C')
        self._seed_invoice(customer_id, '9200000003', '2026-01-01', lines=[{'product_id': 'RATE_TEST_C', 'product_name': 'Rate Test C', 'quantity': 100}])
        invoice_b = self._seed_invoice(customer_id, '9200000003', '2026-01-11', lines=[{'product_id': 'RATE_TEST_C', 'product_name': 'Rate Test C', 'quantity': 200}])

        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        assert DB['customer_product_daily_consumptions'].count_documents({'customer_id': customer_id, 'product_id': 'RATE_TEST_C'}) == 10

        DB['invoices'].update_one({'id': invoice_b}, {'$set': {'invoice_date': '2026-01-06'}})
        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")

        rows = list(DB['customer_product_daily_consumptions'].find({'customer_id': customer_id, 'product_id': 'RATE_TEST_C'}, {'_id': 0}))
        assert len(rows) == 5
        assert DB['customer_product_daily_consumptions'].count_documents({'customer_id': customer_id, 'product_id': 'RATE_TEST_C', 'date': '2026-01-11'}) == 0

    def test_day_diff_zero_does_not_crash(self):
        customer_id = self._seed_customer('9200000004')
        self._seed_product('RATE_TEST_D', 'Rate Test D')
        self._seed_invoice(customer_id, '9200000004', '2026-01-01', lines=[{'product_id': 'RATE_TEST_D', 'product_name': 'Rate Test D', 'quantity': 25}])
        self._seed_invoice(customer_id, '9200000004', '2026-01-01', lines=[{'product_id': 'RATE_TEST_D', 'product_name': 'Rate Test D', 'quantity': 25}])

        response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        assert response.status_code == 200
        assert DB['customer_product_daily_consumptions'].count_documents({'customer_id': customer_id, 'product_id': 'RATE_TEST_D'}) == 0

    def test_cancelled_invoices_are_excluded(self):
        customer_id = self._seed_customer('9200000005')
        self._seed_product('RATE_TEST_E', 'Rate Test E')
        self._seed_invoice(customer_id, '9200000005', '2026-01-01', is_cancelled=True, lines=[{'product_id': 'RATE_TEST_E', 'product_name': 'Rate Test E', 'quantity': 50}])
        self._seed_invoice(customer_id, '9200000005', '2026-01-05', lines=[{'product_id': 'RATE_TEST_E', 'product_name': 'Rate Test E', 'quantity': 50}])

        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        assert DB['customer_product_daily_consumptions'].count_documents({'customer_id': customer_id, 'product_id': 'RATE_TEST_E'}) == 0
        aggregate = DB['customer_product_consumptions'].find_one({'customer_id': customer_id, 'product_id': 'RATE_TEST_E'}, {'_id': 0})
        assert aggregate['daily_consumption'] is None

    def test_alias_match_used_when_product_id_missing(self):
        customer_id = self._seed_customer('9200000006')
        self._seed_product('RATE_TEST_F', 'Rate Test F')
        self._seed_alias('Rate Test F Alias', 'RATE_TEST_F')
        self._seed_invoice(customer_id, '9200000006', '2026-01-01', lines=[{'product_name': 'Rate Test F Alias', 'quantity': 30}])
        self._seed_invoice(customer_id, '9200000006', '2026-01-04', lines=[{'product_name': 'Rate Test F Alias', 'quantity': 30}])

        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        assert DB['customer_product_daily_consumptions'].count_documents({'customer_id': customer_id, 'product_id': 'RATE_TEST_F'}) == 3

    def test_weighted_rate_is_persisted(self):
        customer_id = self._seed_customer('9200000007')
        self._seed_product('RATE_TEST_G', 'Rate Test G')
        self._seed_invoice(customer_id, '9200000007', '2026-01-01', lines=[{'product_id': 'RATE_TEST_G', 'product_name': 'Rate Test G', 'quantity': 100}])
        self._seed_invoice(customer_id, '9200000007', '2026-01-11', lines=[{'product_id': 'RATE_TEST_G', 'product_name': 'Rate Test G', 'quantity': 100}])
        self._seed_invoice(customer_id, '9200000007', '2026-01-13', lines=[{'product_id': 'RATE_TEST_G', 'product_name': 'Rate Test G', 'quantity': 100}])

        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        aggregate = DB['customer_product_consumptions'].find_one({'customer_id': customer_id, 'product_id': 'RATE_TEST_G'}, {'_id': 0})
        assert round(aggregate['rate_mt_weighted'], 4) == 16.6667
        assert round(aggregate['daily_consumption'], 4) == 30.0

    def test_get_consumption_backward_compatible(self):
        customer_id = self._seed_customer('9200000008')
        self._seed_product('RATE_TEST_H', 'Rate Test H')
        self._seed_invoice(customer_id, '9200000008', '2026-01-01', lines=[{'product_id': 'RATE_TEST_H', 'product_name': 'Rate Test H', 'quantity': 40}])
        self._seed_invoice(customer_id, '9200000008', '2026-01-05', lines=[{'product_id': 'RATE_TEST_H', 'product_name': 'Rate Test H', 'quantity': 20}])

        self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        response = self.session.get(f"{BASE_URL}/api/customers/{customer_id}/consumption")
        assert response.status_code == 200
        item = response.json()['data'][0]
        for key in ['product_id', 'product_name', 'daily_consumption', 'average_order_quantity', 'last_invoice_date', 'last_quantity']:
            assert key in item
