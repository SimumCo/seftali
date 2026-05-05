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
from services.seftali.core import get_route_info, WEEKDAY_CODES
from utils.auth import hash_password

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
CFG = dotenv_values('/app/backend/.env')
CLIENT = MongoClient(CFG['MONGO_URL'])
DB = CLIENT[CFG['DB_NAME']]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def pick_route_days_with_diff():
    for first in WEEKDAY_CODES:
        for second in WEEKDAY_CODES:
            if first == second:
                continue
            route_days = [first, second]
            route_info = get_route_info(route_days)
            if route_info['days_to_next_route'] != route_info['supply_days']:
                return route_days, route_info
    raise RuntimeError('No route day combination found with differing days_to_next_route and supply_days')


class TestDraftEngineDualRead:
    def _cleanup(self, customer_id, product_id, username):
        DB['sf_customers'].delete_many({'id': customer_id})
        DB['users'].delete_many({'username': username})
        DB['products'].delete_many({'product_id': product_id})
        DB['de_customer_product_state'].delete_many({'customer_id': customer_id})
        DB['customer_product_consumptions'].delete_many({'customer_id': customer_id})
        DB['sf_system_drafts'].delete_many({'customer_id': customer_id})
        DB['de_weekly_product_multipliers'].delete_many({'product_id': product_id})

    def _seed_customer_and_user(self, customer_id, username, route_days):
        user_id = str(uuid.uuid4())
        DB['users'].insert_one({
            'id': user_id,
            'username': username,
            'password_hash': hash_password('test1234'),
            'full_name': f'Draft User {username}',
            'role': UserRole.CUSTOMER.value,
            'is_active': True,
            'created_at': now_iso(),
        })
        DB['sf_customers'].insert_one({
            'id': customer_id,
            'user_id': user_id,
            'name': f'Draft Customer {customer_id[:6]}',
            'route_plan': {'days': route_days},
            'is_active': True,
            'created_at': now_iso(),
            'updated_at': now_iso(),
        })

    def _seed_product(self, product_id):
        DB['products'].insert_one({
            'product_id': product_id,
            'name': f'Product {product_id[-4:]}',
            'shelf_life_days': 30,
            'created_at': now_iso(),
            'updated_at': now_iso(),
        })

    def _seed_state(self, customer_id, product_id, rate_mt, last_qty=100, interval_count=3):
        DB['de_customer_product_state'].insert_one({
            'customer_id': customer_id,
            'product_id': product_id,
            'prev_delivery_date': '2026-03-01',
            'prev_delivery_qty': last_qty,
            'last_delivery_date': '2026-03-05',
            'last_delivery_qty': last_qty,
            'interval_rates': [rate_mt] * max(interval_count, 1),
            'interval_count': interval_count,
            'rate_mt': rate_mt,
            'weekly_multiplier': 1.0,
            'delivery_count': max(interval_count + 1, 1),
            'age_days': 120,
            'is_active': True,
            'created_at': now_iso(),
            'updated_at': now_iso(),
        })

    def _seed_aggregate(self, customer_id, product_id, rate_mt_weighted, confidence_score=0.8, interval_count=4, trend='stable', last_qty=120):
        DB['customer_product_consumptions'].insert_one({
            'id': str(uuid.uuid4()),
            'customer_id': customer_id,
            'product_id': product_id,
            'last_invoice_date': datetime.now(timezone.utc).date().isoformat(),
            'last_quantity': last_qty,
            'daily_consumption': 5.0,
            'average_order_quantity': 110.0,
            'estimated_days_to_depletion': None,
            'rate_mt_weighted': rate_mt_weighted,
            'interval_count': interval_count,
            'skipped_interval_count': 0,
            'confidence_score': confidence_score,
            'trend': trend,
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

    def test_draft_uses_rate_mt_weighted_when_available(self):
        customer_id = str(uuid.uuid4())
        product_id = 'DRAFT_DUAL_1'
        username = f'cust_{uuid.uuid4().hex[:10]}'
        route_days, route_info = pick_route_days_with_diff()
        self._cleanup(customer_id, product_id, username)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id)
        self._seed_state(customer_id, product_id, rate_mt=5.0)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=20.0, confidence_score=0.9, interval_count=5)

        draft = self._fetch_draft(username)
        item = draft['items'][0]
        assert item['rate_source'] == 'aggregate'
        assert round(item['rate_mt_weighted'], 4) == 20.0
        assert round(item['need_qty'], 2) == round(20.0 * route_info['days_to_next_route'], 2)

    def test_draft_falls_back_to_state_when_aggregate_missing(self):
        customer_id = str(uuid.uuid4())
        product_id = 'DRAFT_DUAL_2'
        username = f'cust_{uuid.uuid4().hex[:10]}'
        route_days, route_info = pick_route_days_with_diff()
        self._cleanup(customer_id, product_id, username)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id)
        self._seed_state(customer_id, product_id, rate_mt=6.0)

        draft = self._fetch_draft(username)
        item = draft['items'][0]
        assert item['rate_source'] == 'state'
        assert round(item['rate_mt'], 4) == 6.0
        assert item['rate_mt_weighted'] is None
        assert round(item['need_qty'], 2) == round(6.0 * route_info['days_to_next_route'], 2)

    def test_draft_uses_days_to_next_route_not_supply_days(self):
        customer_id = str(uuid.uuid4())
        product_id = 'DRAFT_DUAL_3'
        username = f'cust_{uuid.uuid4().hex[:10]}'
        route_days, route_info = pick_route_days_with_diff()
        self._cleanup(customer_id, product_id, username)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=10.0, confidence_score=0.8, interval_count=3)

        draft = self._fetch_draft(username)
        item = draft['items'][0]
        assert route_info['days_to_next_route'] != route_info['supply_days']
        assert round(item['need_qty'], 2) == round(10.0 * route_info['days_to_next_route'], 2)
        assert round(item['need_qty'], 2) != round(10.0 * route_info['supply_days'], 2)

    def test_low_confidence_flag_set_when_confidence_low(self):
        customer_id = str(uuid.uuid4())
        product_id = 'DRAFT_DUAL_4'
        username = f'cust_{uuid.uuid4().hex[:10]}'
        route_days, _ = pick_route_days_with_diff()
        self._cleanup(customer_id, product_id, username)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=8.0, confidence_score=0.2, interval_count=1)

        draft = self._fetch_draft(username)
        item = draft['items'][0]
        assert item['flags']['low_confidence'] is True
        assert round(item['confidence_score'], 4) == 0.2

    def test_backward_compatible_response_not_broken(self):
        customer_id = str(uuid.uuid4())
        product_id = 'DRAFT_DUAL_5'
        username = f'cust_{uuid.uuid4().hex[:10]}'
        route_days, _ = pick_route_days_with_diff()
        self._cleanup(customer_id, product_id, username)
        self._seed_customer_and_user(customer_id, username, route_days)
        self._seed_product(product_id)
        self._seed_aggregate(customer_id, product_id, rate_mt_weighted=12.0, confidence_score=0.8, interval_count=4)

        draft = self._fetch_draft(username)
        item = draft['items'][0]
        for key in ['product_id', 'product_name', 'suggested_qty', 'need_qty', 'weekly_multiplier', 'rate_used', 'flags']:
            assert key in item
        assert draft['calculation_params']['formula_version'] == 'v2-dual-read'
