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


class TestCustomerChangePassword:
    def _create_customer_and_user(self, username: str, *, user_active=True, customer_active=True, must_change_password=True, password=DEFAULT_CUSTOMER_PASSWORD):
        customer_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        DB['customer_users'].delete_many({'username': username})
        DB['customers'].delete_many({'identity_number': username})

        DB['customers'].insert_one({
            'id': customer_id,
            'salesperson_id': '80ddfb6a-0bac-465b-a32f-0f119802661b',
            'business_name': f'Password Customer {username}',
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

    def _login(self, username: str, password: str):
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/login",
            json={'username': username, 'password': password},
            timeout=30,
        )
        return response

    def test_password_changed_successfully(self):
        self._create_customer_and_user('8333333331')
        login_response = self._login('8333333331', DEFAULT_CUSTOMER_PASSWORD)
        token = login_response.json()['data']['token']
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={'current_password': DEFAULT_CUSTOMER_PASSWORD, 'new_password': 'YeniSifre123!'},
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        assert response.status_code == 200
        assert response.json()['success'] is True
        assert response.json()['must_change_password'] is False

    def test_must_change_password_false_after_change(self):
        self._create_customer_and_user('8333333332')
        token = self._login('8333333332', DEFAULT_CUSTOMER_PASSWORD).json()['data']['token']
        requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={'current_password': DEFAULT_CUSTOMER_PASSWORD, 'new_password': 'YeniSifre123!'},
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        user = DB['customer_users'].find_one({'username': '8333333332'}, {'_id': 0})
        assert user['must_change_password'] is False
        assert user.get('password_changed_at')

    def test_wrong_current_password_fails(self):
        self._create_customer_and_user('8333333333')
        token = self._login('8333333333', DEFAULT_CUSTOMER_PASSWORD).json()['data']['token']
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={'current_password': 'wrong', 'new_password': 'YeniSifre123!'},
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        assert response.status_code == 401
        assert response.json()['detail'] == 'invalid current password'

    def test_same_password_not_allowed(self):
        self._create_customer_and_user('8333333334')
        token = self._login('8333333334', DEFAULT_CUSTOMER_PASSWORD).json()['data']['token']
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={'current_password': DEFAULT_CUSTOMER_PASSWORD, 'new_password': DEFAULT_CUSTOMER_PASSWORD},
            headers={'Authorization': f'Bearer {token}'},
            timeout=30,
        )
        assert response.status_code == 400
        assert response.json()['detail'] == 'same password not allowed'

    def test_unauthorized_request_rejected(self):
        response = requests.post(
            f"{BASE_URL}/api/auth/customer/change-password",
            json={'current_password': DEFAULT_CUSTOMER_PASSWORD, 'new_password': 'YeniSifre123!'},
            timeout=30,
        )
        assert response.status_code in (401, 403)

    def test_inactive_user_or_customer_cannot_change(self):
        self._create_customer_and_user('8333333335', user_active=False)
        login_response = self._login('8333333335', DEFAULT_CUSTOMER_PASSWORD)
        assert login_response.status_code == 401

        self._create_customer_and_user('8333333336', customer_active=False)
        login_response = self._login('8333333336', DEFAULT_CUSTOMER_PASSWORD)
        assert login_response.status_code == 401
