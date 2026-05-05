from services.seftali.core import now_utc, to_iso
from config.database import db
from repositories.gib_import_repository import GIBImportRepository
from utils.auth import ALGORITHM, SECRET_KEY, create_access_token, hash_password, verify_password
import jwt
import re


class CustomerLoginError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CustomerAuthService:
    """Customer login and password-change flow for customer_users collection."""

    def __init__(self):
        self.repository = GIBImportRepository(db)

    @staticmethod
    def _validate_new_password(password: str):
        if not password:
            raise CustomerLoginError('new_password boş olamaz', 400)
        if len(password) < 8:
            raise CustomerLoginError('weak new password', 400)
        if not re.search(r'[A-Za-z]', password) or not re.search(r'\d', password):
            raise CustomerLoginError('weak new password', 400)

    async def login(self, username: str, password: str) -> dict:
        if not username:
            raise CustomerLoginError('username boş olamaz', 400)
        if not password:
            raise CustomerLoginError('password boş olamaz', 400)

        user = await self.repository.find_customer_user_by_username(username)
        if not user:
            raise CustomerLoginError('user not found', 401)

        if not verify_password(password, user['password_hash']):
            raise CustomerLoginError('invalid password', 401)

        if not user.get('is_active', True):
            raise CustomerLoginError('inactive user', 401)

        customer = await self.repository.find_customer_by_id(user['customer_id'])
        if not customer:
            raise CustomerLoginError('customer not found', 401)

        if not customer.get('is_active', True):
            raise CustomerLoginError('inactive customer', 401)

        token = create_access_token({
            'sub': user['id'],
            'role': 'customer',
            'customer_id': customer['id'],
            'auth_type': 'customer_users',
        })

        await self.repository.update_customer_user(user['id'], {'last_login_at': to_iso(now_utc())})

        return {
            'customer_id': customer['id'],
            'user_id': user['id'],
            'username': user['username'],
            'must_change_password': bool(user.get('must_change_password', True)),
            'token': token,
            'customer': {
                'business_name': customer.get('business_name'),
                'customer_type': customer.get('customer_type'),
                'status': 'active' if customer.get('is_active', True) else 'inactive',
            },
        }

    async def get_authenticated_context(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.PyJWTError as exc:
            raise CustomerLoginError('unauthorized', 401) from exc

        if payload.get('auth_type') != 'customer_users':
            raise CustomerLoginError('unauthorized', 401)

        user_id = payload.get('sub')
        if not user_id:
            raise CustomerLoginError('unauthorized', 401)

        user = await self.repository.find_customer_user_by_id(user_id)
        if not user:
            raise CustomerLoginError('user not found', 401)
        if not user.get('is_active', True):
            raise CustomerLoginError('inactive user', 401)

        customer = await self.repository.find_customer_by_id(user['customer_id'])
        if not customer:
            raise CustomerLoginError('customer not found', 401)
        if not customer.get('is_active', True):
            raise CustomerLoginError('inactive customer', 401)

        return user, customer

    async def change_password(self, token: str, current_password: str, new_password: str) -> dict:
        if not current_password:
            raise CustomerLoginError('current_password boş olamaz', 400)

        user, _customer = await self.get_authenticated_context(token)

        if not verify_password(current_password, user['password_hash']):
            raise CustomerLoginError('invalid current password', 401)
        if current_password == new_password:
            raise CustomerLoginError('same password not allowed', 400)

        self._validate_new_password(new_password)

        await self.repository.update_customer_user(
            user['id'],
            {
                'password_hash': hash_password(new_password),
                'must_change_password': False,
                'password_changed_at': to_iso(now_utc()),
            },
        )

        return {
            'success': True,
            'must_change_password': False,
        }
