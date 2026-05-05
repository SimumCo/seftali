import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

sys.path.insert(0, '/app/backend')
from models.user import UserRole
from services.seftali.core import WEEKDAY_CODES
from utils.auth import hash_password

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
CFG = dotenv_values('/app/backend/.env')
CLIENT = MongoClient(CFG['MONGO_URL'])
DB = CLIENT[CFG['DB_NAME']]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def current_week_start():
    today = datetime.now(timezone.utc).date()
    return (today - timedelta(days=today.weekday())).isoformat()


class TestWeeklyMultiplierLookup:
    def _cleanup(self, customer_id, username, product_id):
        DB['sf_customers'].delete_many({'id': customer_id})
        DB['users'].delete_many({'username': username})
        DB['products'].delete_many({'product_id': product_id})
        DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        DB['de_weekly_product_multipliers'].delete_many({'product_id': product_id})

    def _seed_customer_and_user(self, customer_id, username, *, depot_id=None, segment_id=None, customer_type=None):
        user_id = str(uuid.uuid4())
        DB['users'].insert_one({
            'id': user_id,
            'username': username,
            'password_hash': hash_password('test1234'),
            'full_name': f'Multiplier User {username}',
            'role': UserRole.CUSTOMER.value,
            'is_active': True,
            'created_at': now_iso(),
        })
        customer_doc = {
            'id': customer_id,
            'user_id': user_id,
            'name': f'Multiplier Customer {customer_id[:6]}',
            'route_plan': {'days': ['MON', 'FRI']},
            'is_active': True,
            'created_at': now_iso(),
            'updated_at': now_iso(),
        }
        if depot_id is not None:
            customer_doc['depot_id'] = depot_id
        if segment_id is not None:
            customer_doc['segment_id'] = segment_id
        if customer_type is not None:
            customer_doc['customer_type'] = customer_type
        DB['sf_customers'].insert_one(customer_doc)

    def _seed_product(self, product_id):
        DB['products'].insert_one({
            'product_id': product_id,
            'name': f'Product {product_id[-4:]}',
            'shelf_life_days': 30,
            'created_at': now_iso(),
            'updated_at': now_iso(),
        })

    def _seed_aggregate(self, customer_id, product_id, rate_mt_weighted=10.0):
        DB['customer_product_consumptions'].insert_one({
            'id': str(uuid.uuid4()),
            'customer_id': customer_id,
            'product_id': product_id,
            'last_invoice_date': datetime.now(timezone.utc).date().isoformat(),
            'last_quantity': 100,
            'daily_consumption': 10.0,
            'average_order_quantity': 100.0,
            'estimated_days_to_depletion': None,
            'rate_mt_weighted': rate_mt_weighted,
            'interval_count': 4,
            'skipped_interval_count': 0,
            'confidence_score': 0.8,
            'trend': 'stable',
            'invoice_count': 5,
            'normalization_source': 'direct',
            'last_calculated_at': now_iso(),
            'created_at': now_iso(),
            'updated_at': now_iso(),
        })

    def _seed_multiplier(self, product_id, multiplier, *, depot_id=None, segment_id=None):
        DB['de_weekly_product_multipliers'].insert_one({
            'id': str(uuid.uuid4()),
            'week_start': current_week_start(),
            'product_id': product_id,
            'multiplier': multiplier,
            'depot_id': depot_id,
            'segment_id': segment_id,
            'created_at': now_iso(),
            'updated_at': now_iso(),
        })

    def _fetch_draft(self, username):
        login = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={'username': username, 'password': 'test1234'},
            timeout=30,
        )
        assert login.status_code == 200, login.text
        token = login.json()['access_token']
        response = requests.get(
            f"{BASE_URL}/api/seftali/customer/draft",
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        assert response.status_code == 200, response.text
        return response.json()['data']

    def test_multiplier_uses_depot_segment_product_when_available(self):
        customer_id = str(uuid.uuid4())
        username = f'mult_{uuid.uuid4().hex[:8]}'
        product_id = 'MULT_TEST_1'
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, depot_id='D1', segment_id='S1')
        self._seed_product(product_id)
        self._seed_aggregate(customer_id, product_id)
        self._seed_multiplier(product_id, 1.4, depot_id='D1', segment_id='S1')
        self._seed_multiplier(product_id, 1.2, segment_id='S1')
        self._seed_multiplier(product_id, 1.1)

        item = self._fetch_draft(username)['items'][0]
        assert item['weekly_multiplier'] == 1.4
        assert item['weekly_multiplier_source'] == 'depot_segment_product'

    def test_multiplier_falls_back_to_segment_product(self):
        customer_id = str(uuid.uuid4())
        username = f'mult_{uuid.uuid4().hex[:8]}'
        product_id = 'MULT_TEST_2'
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, segment_id='S2')
        self._seed_product(product_id)
        self._seed_aggregate(customer_id, product_id)
        self._seed_multiplier(product_id, 1.25, segment_id='S2')
        self._seed_multiplier(product_id, 1.1)

        item = self._fetch_draft(username)['items'][0]
        assert item['weekly_multiplier'] == 1.25
        assert item['weekly_multiplier_source'] == 'segment_product'

    def test_multiplier_falls_back_to_product_only(self):
        customer_id = str(uuid.uuid4())
        username = f'mult_{uuid.uuid4().hex[:8]}'
        product_id = 'MULT_TEST_3'
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username)
        self._seed_product(product_id)
        self._seed_aggregate(customer_id, product_id)
        self._seed_multiplier(product_id, 1.15)

        item = self._fetch_draft(username)['items'][0]
        assert item['weekly_multiplier'] == 1.15
        assert item['weekly_multiplier_source'] == 'product_only'

    def test_multiplier_defaults_to_one_when_missing(self):
        customer_id = str(uuid.uuid4())
        username = f'mult_{uuid.uuid4().hex[:8]}'
        product_id = 'MULT_TEST_4'
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, depot_id='D2', segment_id='S2')
        self._seed_product(product_id)
        self._seed_aggregate(customer_id, product_id)

        item = self._fetch_draft(username)['items'][0]
        assert item['weekly_multiplier'] == 1.0
        assert item['weekly_multiplier_source'] == 'default'

    def test_draft_response_includes_weekly_multiplier_source(self):
        customer_id = str(uuid.uuid4())
        username = f'mult_{uuid.uuid4().hex[:8]}'
        product_id = 'MULT_TEST_5'
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, segment_id='S5')
        self._seed_product(product_id)
        self._seed_aggregate(customer_id, product_id)
        self._seed_multiplier(product_id, 1.3, segment_id='S5')

        item = self._fetch_draft(username)['items'][0]
        assert 'weekly_multiplier_source' in item
        assert item['weekly_multiplier_source'] == 'segment_product'
