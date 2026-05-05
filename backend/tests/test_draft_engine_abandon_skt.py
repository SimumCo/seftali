import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

sys.path.insert(0, '/app/backend')
from models.user import UserRole
from services.seftali.core import WEEKDAY_CODES, get_route_info
from utils.auth import hash_password

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
CFG = dotenv_values('/app/backend/.env')
CLIENT = MongoClient(CFG['MONGO_URL'])
DB = CLIENT[CFG['DB_NAME']]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def pick_route_days_with_long_gap(min_days=4):
    best = None
    best_info = None
    for day in WEEKDAY_CODES:
        route_days = [day]
        info = get_route_info(route_days)
        if info['days_to_next_route'] >= min_days:
            return route_days, info
        if best is None or info['days_to_next_route'] > best_info['days_to_next_route']:
            best, best_info = route_days, info
    return best, best_info


class TestDraftEngineAbandonAndSkt:
    def _cleanup(self, customer_id, username, product_id):
        DB['sf_customers'].delete_many({'id': customer_id})
        DB['users'].delete_many({'username': username})
        DB['products'].delete_many({'product_id': product_id})
        DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        DB['sf_system_drafts'].delete_many({'customer_id': customer_id})

    def _seed_customer_and_user(self, customer_id, username, route_days):
        user_id = str(uuid.uuid4())
        DB['users'].insert_one({
            'id': user_id,
            'username': username,
            'password_hash': hash_password('test1234'),
            'full_name': f'Abandon User {username}',
            'role': UserRole.CUSTOMER.value,
            'is_active': True,
            'created_at': now_iso(),
        })
        DB['sf_customers'].insert_one({
            'id': customer_id,
            'user_id': user_id,
            'name': f'Abandon Customer {customer_id[:6]}',
            'route_plan': {'days': route_days},
            'is_active': True,
            'created_at': now_iso(),
            'updated_at': now_iso(),
        })

    def _seed_product(self, product_id, shelf_life_days=None):
        product = {
            'product_id': product_id,
            'name': f'Product {product_id[-4:]}',
            'created_at': now_iso(),
            'updated_at': now_iso(),
        }
        if shelf_life_days is not None:
            product['shelf_life_days'] = shelf_life_days
        DB['products'].insert_one(product)

    def _seed_aggregate(self, customer_id, product_id, *, rate_mt_weighted, last_quantity, last_invoice_date, confidence_score=0.8, interval_count=4):
        DB['customer_product_consumptions'].insert_one({
            'id': str(uuid.uuid4()),
            'customer_id': customer_id,
            'product_id': product_id,
            'last_invoice_date': last_invoice_date,
            'last_quantity': last_quantity,
            'daily_consumption': None,
            'average_order_quantity': 100.0,
            'estimated_days_to_depletion': None,
            'rate_mt_weighted': rate_mt_weighted,
            'interval_count': interval_count,
            'skipped_interval_count': 0,
            'confidence_score': confidence_score,
            'trend': 'stable',
            'invoice_count': interval_count + 1,
            'normalization_source': 'direct',
            'last_calculated_at': now_iso(),
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

    def test_product_excluded_when_abandon_rule_triggered(self):
        customer_id = str(uuid.uuid4())
        username = f'abandon_{uuid.uuid4().hex[:8]}'
        product_id = 'ABANDON_TEST_1'
        route_days, _ = pick_route_days_with_long_gap()
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id, shelf_life_days=30)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=10.0, last_quantity=5, last_invoice_date='2026-01-01')

        draft = self._fetch_draft(username)
        assert len(draft['items']) == 0
        assert len(draft['excluded_items']) == 1
        assert draft['excluded_items'][0]['abandoned'] is True

    def test_product_not_excluded_when_recent_enough(self):
        customer_id = str(uuid.uuid4())
        username = f'abandon_{uuid.uuid4().hex[:8]}'
        product_id = 'ABANDON_TEST_2'
        route_days, _ = pick_route_days_with_long_gap()
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id, shelf_life_days=30)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=10.0, last_quantity=500, last_invoice_date=datetime.now(timezone.utc).date().isoformat())

        draft = self._fetch_draft(username)
        assert len(draft['items']) == 1
        assert draft['items'][0]['abandoned'] is False

    def test_abandon_rule_skipped_when_rate_missing(self):
        customer_id = str(uuid.uuid4())
        username = f'abandon_{uuid.uuid4().hex[:8]}'
        product_id = 'ABANDON_TEST_3'
        route_days, _ = pick_route_days_with_long_gap()
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id, shelf_life_days=30)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=None, last_quantity=500, last_invoice_date='2026-01-01', confidence_score=0.0, interval_count=0)

        draft = self._fetch_draft(username)
        assert len(draft['items']) == 1
        assert draft['items'][0]['abandoned'] is False

    def test_skt_clamp_limits_need_qty(self):
        customer_id = str(uuid.uuid4())
        username = f'abandon_{uuid.uuid4().hex[:8]}'
        product_id = 'ABANDON_TEST_4'
        route_days, route_info = pick_route_days_with_long_gap()
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id, shelf_life_days=2)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=10.0, last_quantity=1000, last_invoice_date=datetime.now(timezone.utc).date().isoformat())

        draft = self._fetch_draft(username)
        item = draft['items'][0]
        assert route_info['days_to_next_route'] >= 2
        assert item['pre_clamp_need_qty'] >= item['final_need_qty']
        assert item['was_clamped'] is True
        assert item['need_qty'] == item['final_need_qty']
        assert item['max_safe_qty'] == 20.0

    def test_no_clamp_when_shelf_life_missing(self):
        customer_id = str(uuid.uuid4())
        username = f'abandon_{uuid.uuid4().hex[:8]}'
        product_id = 'ABANDON_TEST_5'
        route_days, _ = pick_route_days_with_long_gap()
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id, shelf_life_days=None)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=10.0, last_quantity=1000, last_invoice_date=datetime.now(timezone.utc).date().isoformat())

        item = self._fetch_draft(username)['items'][0]
        assert item['was_clamped'] is False
        assert item['clamp_reason'] is None

    def test_no_clamp_when_rate_invalid(self):
        customer_id = str(uuid.uuid4())
        username = f'abandon_{uuid.uuid4().hex[:8]}'
        product_id = 'ABANDON_TEST_6'
        route_days, _ = pick_route_days_with_long_gap()
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id, shelf_life_days=2)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=None, last_quantity=1000, last_invoice_date=datetime.now(timezone.utc).date().isoformat(), confidence_score=0.0, interval_count=0)

        item = self._fetch_draft(username)['items'][0]
        assert item['was_clamped'] is False
        assert item['need_qty'] is None

    def test_response_contains_abandon_and_clamp_debug_fields(self):
        customer_id = str(uuid.uuid4())
        username = f'abandon_{uuid.uuid4().hex[:8]}'
        product_id = 'ABANDON_TEST_7'
        route_days, _ = pick_route_days_with_long_gap()
        self._cleanup(customer_id, username, product_id)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id, shelf_life_days=2)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=10.0, last_quantity=1000, last_invoice_date=datetime.now(timezone.utc).date().isoformat())

        item = self._fetch_draft(username)['items'][0]
        for key in ['abandoned', 'abandoned_reason', 'expected_depletion_days', 'days_since_last_delivery', 'pre_clamp_need_qty', 'final_need_qty', 'coverage_days', 'shelf_life_days', 'was_clamped', 'clamp_reason', 'max_safe_qty']:
            assert key in item
