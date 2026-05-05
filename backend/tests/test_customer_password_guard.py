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


class TestCustomerPasswordGuard:
    def _create_customer_and_user(self, username: str, *, must_change_password=True):
        customer_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        DB['customer_users'].delete_many({'username': username})
        DB['customers'].delete_many({'identity_number': username})

        DB['customers'].insert_one({
            'id': customer_id,
            'salesperson_id': '80ddfb6a-0bac-465b-a32f-0f119802661b',
            'business_name': f'Guard Customer {username}',
            'tax_no': username,
            'identity_number': username,
            'customer_type': 'retail',
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        })
        DB['customer_users'].insert_one({
            'id': user_id,
            'customer_id': customer_id,
            'username': username,
            'password_hash': hash_password(DEFAULT_CUSTOMER_PASSWORD),
            'must_change_password': must_change_password,
            'is_active': True,
            'created_at': now,
            'updated_at': now,
        })
        return customer_id, user_id

    def _login(self, username: str, password: str = DEFAULT_CUSTOMER_PASSWORD):
        return requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={'username': username, 'password': password},
            timeout=30,
        )

    def test_password_change_required_blocks_normal_endpoint(self):
        self._create_customer_and_user('8555555551', must_change_password=True)
        login = self._login('8555555551')
        token = login.json()['data']['token']
        response = requests.get(
            f"{BASE_URL}/api/seftali/customer/profile",
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        assert response.status_code == 403
        payload = response.json()
        assert payload['error'] == 'PASSWORD_CHANGE_REQUIRED'

    def test_change_password_endpoint_is_allowed(self):
        self._create_customer_and_user('8555555552', must_change_password=True)
        token = self._login('8555555552').json()['data']['token']
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={'current_password': DEFAULT_CUSTOMER_PASSWORD, 'new_password': 'YeniSifre123!'},
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        assert response.status_code == 200
        assert response.json()['must_change_password'] is False

    def test_access_opens_after_password_change(self):
        self._create_customer_and_user('8555555553', must_change_password=True)
        token = self._login('8555555553').json()['data']['token']
        change = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={'current_password': DEFAULT_CUSTOMER_PASSWORD, 'new_password': 'YeniSifre123!'},
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        assert change.status_code == 200
        relogin = self._login('8555555553', 'YeniSifre123!')
        new_token = relogin.json()['data']['token']
        response = requests.get(
            f"{BASE_URL}/api/seftali/customer/profile",
            headers={'Authorization': f'Bearer {new_token}'},
            timeout=30,
        )
        assert response.status_code == 200

    def test_false_flag_user_accesses_normally(self):
        self._create_customer_and_user('8555555554', must_change_password=False)
        token = self._login('8555555554').json()['data']['token']
        response = requests.get(
            f"{BASE_URL}/api/seftali/customer/profile",
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        assert response.status_code == 200
