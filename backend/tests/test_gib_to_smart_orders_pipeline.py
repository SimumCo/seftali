import os
import uuid

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
CFG = dotenv_values('/app/backend/.env')
DEFAULT_CUSTOMER_PASSWORD = CFG['DEFAULT_CUSTOMER_PASSWORD']
CLIENT = MongoClient(CFG['MONGO_URL'])
DB = CLIENT[CFG['DB_NAME']]
SALESPERSON_ID = '80ddfb6a-0bac-465b-a32f-0f119802661b'


class TestGibToSmartOrdersPipeline:
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

    def _reset_identity(self, identity_number: str):
        invoices = list(DB['invoices'].find({'identity_number': identity_number}, {'_id': 0, 'id': 1}))
        invoice_ids = [item['id'] for item in invoices]
        customer_ids = [item['id'] for item in DB['customers'].find({'identity_number': identity_number}, {'_id': 0, 'id': 1})]
        DB['invoice_lines'].delete_many({'invoice_id': {'$in': invoice_ids}})
        DB['invoices'].delete_many({'identity_number': identity_number})
        DB['draft_customers'].delete_many({'identity_number': identity_number})
        DB['customer_product_daily_consumptions'].delete_many({'customer_id': {'$in': customer_ids}})
        DB['customer_product_consumptions'].delete_many({'customer_id': {'$in': customer_ids}})
        DB['customer_users'].delete_many({'username': identity_number})
        DB['customers'].delete_many({'identity_number': identity_number})
        DB['sf_customers'].delete_many({'identity_number': identity_number})

    def test_full_pipeline_import_to_smart_orders(self):
        self._reset_identity('1111111111')
        import_response = self.session.post(f"{BASE_URL}/api/gib/import/start")
        assert import_response.status_code == 200

        drafts_response = self.session.get(f"{BASE_URL}/api/draft-customers", params={'salespersonId': SALESPERSON_ID})
        assert drafts_response.status_code == 200
        drafts = drafts_response.json()['data']
        assert drafts
        draft = next((item for item in drafts if (item.get('tax_number') or item.get('identity_number')) == '1111111111'), drafts[0])

        approve_response = self.session.post(
            f"{BASE_URL}/api/draft-customers/{draft['id']}/approve",
            json={
                'customer_type': 'retail',
                'risk_limit': 10000,
                'balance': 0,
                'phone': '05000000000',
                'address': 'Istanbul',
            },
        )
        assert approve_response.status_code == 200
        approve_data = approve_response.json()['data']
        customer_id = approve_data['customer_id']

        sf_customer = DB['sf_customers'].find_one({'customer_id': customer_id}, {'_id': 0})
        assert sf_customer is not None
        assert sf_customer['salesperson_id'] == SALESPERSON_ID
        assert sf_customer.get('route_plan', {}).get('days')

        link_response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/link-invoices")
        assert link_response.status_code == 200

        recalc_response = self.session.post(f"{BASE_URL}/api/customers/{customer_id}/recalculate-consption")
        assert recalc_response.status_code == 200

        smart_draft_response = self.session.get(f"{BASE_URL}/api/seftali/sales/smart-draft-v2")
        assert smart_draft_response.status_code == 200
        payload = smart_draft_response.json()['data']
        customers = payload.get('customers') or []
        assert customers

        linked_customer = next((item for item in customers if item.get('customer_id') == customer_id), None)
        assert linked_customer is not None
        all_items = linked_customer.get('items', [])
        excluded_items = linked_customer.get('excluded_items', [])
        assert isinstance(all_items, list)
        assert isinstance(excluded_items, list)
        assert all_items or excluded_items, 'smart-draft-v2 should return calculated items or excluded items for linked customer'
        combined = all_items + excluded_items
        assert any((item.get('final_need_qty') is not None) or item.get('abandoned') for item in combined)
        assert any((item.get('rate_mt_weighted') is not None) or (item.get('rate_source') == 'state') for item in combined)

        customer_login = requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={'username': approve_data['username'], 'password': DEFAULT_CUSTOMER_PASSWORD},
            timeout=30,
        )
        assert customer_login.status_code == 200
        customer_token = customer_login.json()['data']['token']

        blocked_daily = requests.get(
            f"{BASE_URL}/api/seftali/customer/daily-consumption",
            headers={'Authorization': f'Bearer {customer_token}'},
            timeout=30,
        )
        assert blocked_daily.status_code == 403
        assert blocked_daily.json()['error'] == 'PASSWORD_CHANGE_REQUIRED'

        change_password = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={'current_password': DEFAULT_CUSTOMER_PASSWORD, 'new_password': 'YeniSifre123!'},
            headers={'Authorization': f'Bearer {customer_token}'},
            timeout=30,
        )
        assert change_password.status_code == 200

        relogin = requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={'username': approve_data['username'], 'password': 'YeniSifre123!'},
            timeout=30,
        )
        assert relogin.status_code == 200
        customer_token = relogin.json()['data']['token']

        customer_daily = requests.get(
            f"{BASE_URL}/api/seftali/customer/daily-consumption",
            headers={'Authorization': f'Bearer {customer_token}'},
            timeout=30,
        )
        assert customer_daily.status_code == 200
        daily_rows = customer_daily.json()['data']
        assert isinstance(daily_rows, list)
        assert daily_rows
        assert 'rate_mt_weighted' in daily_rows[0]
