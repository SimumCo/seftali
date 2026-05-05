from datetime import datetime, timezone
import uuid

from config.database import Database, db
from repositories.gib_import_repository import GIBImportRepository
from services.gib_import.constants import DEFAULT_CUSTOMER_PASSWORD, DRAFT_STATUS_APPROVED, PASSWORD_CHANGE_REQUIRED
from services.gib_import.contracts import CustomerRecord, CustomerUserRecord
from utils.auth import hash_password


class DraftApprovalError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CustomerApprovalService:
    """Approves draft customers and creates customer + customer_user + sf_customer bridge."""

    def __init__(self):
        self.repository = GIBImportRepository(db)
        self.client = Database.get_client()

    async def approve(self, draft_customer_id: str, payload: dict) -> dict:
        try:
            async with await self.client.start_session() as session:
                async with session.start_transaction():
                    return await self._approve_in_session(draft_customer_id, payload, session)
        except DraftApprovalError:
            raise
        except Exception as exc:
            if 'Transaction numbers are only allowed' in str(exc) or 'replica set' in str(exc).lower():
                return await self._approve_in_session(draft_customer_id, payload, session=None)
            raise

    async def _resolve_route_days(self, draft: dict, session=None):
        route_plan = draft.get('route_plan') or {}
        route_days = route_plan.get('days') if isinstance(route_plan, dict) else None
        if route_days:
            return route_days

        salesperson = await self.repository.find_salesperson_user(draft['salesperson_id'], session=session)
        salesperson_route = (salesperson or {}).get('route_plan') if salesperson else None
        if isinstance(salesperson_route, dict) and salesperson_route.get('days'):
            return salesperson_route['days']
        if isinstance(salesperson_route, list) and salesperson_route:
            return salesperson_route

        context_sf_customer = await self.repository.find_sf_customer_context(draft['salesperson_id'], session=session)
        context_route = (context_sf_customer or {}).get('route_plan') if context_sf_customer else None
        if isinstance(context_route, dict) and context_route.get('days'):
            return context_route['days']
        if isinstance(context_route, list) and context_route:
            return context_route

        return ['MON', 'FRI']

    async def _ensure_sf_customer_bridge(self, draft: dict, customer: dict, user: dict, session=None):
        identity_number = customer.get('identity_number') or customer.get('tc_no') or customer.get('tax_no')
        existing_sf_customer = await self.repository.find_sf_customer_by_customer_id(customer['id'], session=session)
        if existing_sf_customer:
            updates = {}
            if not existing_sf_customer.get('customer_id'):
                updates['customer_id'] = customer['id']
            if not existing_sf_customer.get('identity_number') and identity_number:
                updates['identity_number'] = identity_number
            if updates:
                await self.repository.update_sf_customer(existing_sf_customer['id'], updates, session=session)
                existing_sf_customer = {**existing_sf_customer, **updates}
            return existing_sf_customer

        if identity_number:
            existing_sf_customer = await self.repository.find_sf_customer_by_identity(draft['salesperson_id'], identity_number, session=session)
            if existing_sf_customer:
                updates = {}
                if not existing_sf_customer.get('customer_id'):
                    updates['customer_id'] = customer['id']
                if updates:
                    await self.repository.update_sf_customer(existing_sf_customer['id'], updates, session=session)
                    existing_sf_customer = {**existing_sf_customer, **updates}
                return existing_sf_customer

        route_days = await self._resolve_route_days(draft, session=session)
        salesperson = await self.repository.find_salesperson_user(draft['salesperson_id'], session=session) or {}
        context_sf_customer = await self.repository.find_sf_customer_context(draft['salesperson_id'], session=session) or {}
        now = datetime.now(timezone.utc).isoformat()

        sf_customer = {
            'id': str(uuid.uuid4()),
            'customer_id': customer['id'],
            'name': customer.get('business_name') or draft.get('business_name') or 'Bilinmeyen İşletme',
            'tax_no': customer.get('tax_no'),
            'tc_no': customer.get('tc_no'),
            'identity_number': identity_number,
            'user_id': user.get('id'),
            'salesperson_id': draft['salesperson_id'],
            'phone': customer.get('phone', ''),
            'address': customer.get('address', ''),
            'email': customer.get('email', ''),
            'channel': customer.get('customer_type') or context_sf_customer.get('channel') or 'retail',
            'route_plan': {'days': route_days},
            'is_active': True,
            'status': 'active',
            'region_id': draft.get('region_id') or salesperson.get('region_id') or context_sf_customer.get('region_id'),
            'depot_id': draft.get('depot_id') or draft.get('depo_id') or salesperson.get('depot_id') or salesperson.get('depo_id') or context_sf_customer.get('depot_id') or context_sf_customer.get('depo_id'),
            'created_at': now,
            'updated_at': now,
        }
        await self.repository.insert_sf_customer(sf_customer, session=session)
        return sf_customer

    async def _approve_in_session(self, draft_customer_id: str, payload: dict, session=None) -> dict:
        draft = await self.repository.find_draft_customer_by_id(draft_customer_id, session=session)
        if not draft:
            raise DraftApprovalError('Draft customer bulunamadı', 404)

        identity_number = draft.get('tc_no') or draft.get('tax_number') or draft.get('identity_number')
        if not identity_number:
            raise DraftApprovalError('Draft customer üzerinde tc_no veya tax_number bulunmuyor', 400)

        username = identity_number
        existing_customer = await self.repository.find_customer_by_identity(identity_number, session=session)
        existing_user = await self.repository.find_customer_user_by_username(username, session=session)

        if existing_user and not existing_customer:
            linked_customer = await self.repository.db['customer_users'].find_one({'username': username}, {'_id': 0}, session=session)
            if linked_customer and linked_customer.get('customer_id'):
                existing_customer = await self.repository.db['customers'].find_one({'id': linked_customer['customer_id']}, {'_id': 0}, session=session)
            if not existing_customer:
                raise DraftApprovalError('Duplicate conflict: username mevcut ama customer kaydı eşlenemedi', 409)

        if existing_user and existing_customer and existing_user.get('customer_id') != existing_customer.get('id'):
            raise DraftApprovalError('Duplicate conflict: username başka bir customer ile bağlı', 409)

        customer = existing_customer
        if not customer:
            customer = CustomerRecord(
                salesperson_id=draft['salesperson_id'],
                draft_customer_id=draft['id'],
                business_name=draft.get('business_name') or 'Bilinmeyen İşletme',
                tax_no=draft.get('tax_number') or draft.get('identity_number'),
                tc_no=draft.get('tc_no'),
                identity_number=identity_number,
                customer_type=payload['customer_type'],
                risk_limit=payload['risk_limit'],
                balance=payload['balance'],
                phone=payload['phone'],
                address=payload['address'],
            ).model_dump()
            await self.repository.insert_customer(customer, session=session)

        user = existing_user
        if not user:
            user = CustomerUserRecord(
                customer_id=customer['id'],
                username=username,
                password_hash=hash_password(DEFAULT_CUSTOMER_PASSWORD),
                must_change_password=PASSWORD_CHANGE_REQUIRED,
            ).model_dump()
            await self.repository.insert_customer_user(user, session=session)

        sf_customer = await self._ensure_sf_customer_bridge(draft, customer, user, session=session)

        await self.repository.update_draft_customer(
            draft_customer_id,
            {
                'status': DRAFT_STATUS_APPROVED,
                'approved_at': customer.get('updated_at') or customer.get('created_at'),
                'approved_customer_id': customer['id'],
                'customer_user_id': user['id'],
                'sf_customer_id': sf_customer['id'],
            },
            session=session,
        )

        return {
            'customer_id': customer['id'],
            'username': username,
            'must_change_password': bool(user.get('must_change_password', True)),
        }
