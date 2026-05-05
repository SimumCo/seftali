import os
import sys
import uuid
from datetime import datetime, timezone

import pytest
import requests
from dotenv import dotenv_values
from pymongo import MongoClient

sys.path.insert(0, '/app/backend')
from utils.auth import hash_password

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL', '').rstrip('/')
CFG = dotenv_values('/app/backend/.env')
DEFAULT_CUSTOMER_PASSWORD = CFG['DEFAULT_CUSTOMER_PASSWORD']
CLIENT = MongoClient(CFG['MONGO_URL'])
DB = CLIENT[CFG['DB_NAME']]


class TestCustomerAuthLogin:
    def _create_customer_and_user(self, username: str, *, user_active=True, customer_active=True, must_change_password=True, password=DEFAULT_CUSTOMER_PASSWORD):
        customer_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        DB['customer_users'].delete_many({'username': username})
        DB['customers'].delete_many({'identity_number': username})

        DB['customers'].insert_one({
            'id': customer_id,
            'salesperson_id': '80ddfb6a-0bac-465b-a32f-0f119802661b',
            'business_name': f'Auth Customer {username}',
            'tax_no': username,
            'identity_number': username,
            'customer_type': 'retail',
            'risk_limit': 0,
            'balance': 0,
            'phone': '',
            'address': '',
            'is_active': customer_active,
            'created_at': now,
            'updated_at': now,
        })
        DB['customer_users'].insert_one({
            'id': user_id,
            'customer_id': customer_id,
            'username': username,
            'password_hash': hash_password(password),
            'must_change_password': must_change_password,
            'is_active': user_active,
            'created_at': now,
            'updated_at': now,
        })
        return customer_id, user_id

    def test_customer_login_success(self):
        customer_id, user_id = self._create_customer_and_user('8111111111')
        response = requests.post(f"{BASE_URL}/api/auth/customer/login", json={'username': '8111111111', 'password': DEFAULT_CUSTOMER_PASSWORD}, timeout=30)
        assert response.status_code == 200
        payload = response.json()['data']
        assert payload['customer_id'] == customer_id
        assert payload['user_id'] == user_id
        assert payload['username'] == '8111111111'
        assert payload['must_change_password'] is True
        assert payload['token']

    def test_wrong_password_fails(self):
        self._create_customer_and_user('8111111112')
        response = requests.post(f"{BASE_URL}/api/auth/customer/login", json={'username': '8111111112', 'password': 'wrong'}, timeout=30)
        assert response.status_code == 401
        assert response.json()['detail'] == 'invalid password'

    def test_user_not_found_fails(self):
        response = requests.post(f"{BASE_URL}/api/auth/customer/login", json={'username': 'does-not-exist', 'password': DEFAULT_CUSTOMER_PASSWORD}, timeout=30)
        assert response.status_code == 401
        assert response.json()['detail'] == 'user not found'

    def test_inactive_user_cannot_login(self):
        self._create_customer_and_user('8111111113', user_active=False)
        response = requests.post(f"{BASE_URL}/api/auth/customer/login", json={'username': '8111111113', 'password': DEFAULT_CUSTOMER_PASSWORD}, timeout=30)
        assert response.status_code == 401
        assert response.json()['detail'] == 'inactive user'

    def test_inactive_customer_cannot_login(self):
        self._create_customer_and_user('8111111114', customer_active=False)
        response = requests.post(f"{BASE_URL}/api/auth/customer/login", json={'username': '8111111114', 'password': DEFAULT_CUSTOMER_PASSWORD}, timeout=30)
        assert response.status_code == 401
        assert response.json()['detail'] == 'inactive customer'

    def test_must_change_password_is_returned(self):
        self._create_customer_and_user('8111111115', must_change_password=True)
        response = requests.post(f"{BASE_URL}/api/auth/customer/login", json={'username': '8111111115', 'password': DEFAULT_CUSTOMER_PASSWORD}, timeout=30)
        assert response.status_code == 200
        assert response.json()['data']['must_change_password'] is True
