from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from models.user import UserRole
from services.efatura.contracts import EInvoiceCreateRequest
from services.efatura.invoice_service import EInvoiceService
from services.efatura.provider_adapter import ProviderError
from services.seftali.core import std_resp
from utils.auth import require_role

router = APIRouter(prefix='/invoices', tags=['e-Fatura'])
ALLOWED_ROLES = [UserRole.ADMIN, UserRole.ACCOUNTING, UserRole.SALES_AGENT, UserRole.SALES_REP]


@router.post('/test-smoke')
async def create_test_smoke_invoice(current_user=Depends(require_role(ALLOWED_ROLES))):
    service = EInvoiceService()
    try:
        result = await service.create_test_smoke_invoice()
    except ProviderError as exc:
        raise HTTPException(exc.status_code, {
            'message': exc.message,
            'provider_code': exc.provider_code,
            'provider_message': exc.provider_message,
        }) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return std_resp(True, result.model_dump())


@router.post('')
async def create_invoice(payload: EInvoiceCreateRequest, current_user=Depends(require_role(ALLOWED_ROLES))):
    service = EInvoiceService()
    try:
        result = await service.create_and_send(payload)
    except ProviderError as exc:
        raise HTTPException(exc.status_code, {
            'message': exc.message,
            'provider_code': exc.provider_code,
            'provider_message': exc.provider_message,
        }) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return std_resp(True, result.model_dump())


@router.get('/{invoice_id}')
async def get_invoice(invoice_id: str, current_user=Depends(require_role(ALLOWED_ROLES))):
    service = EInvoiceService()
    invoice = await service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(404, 'invoice not found')
    return std_resp(True, invoice)


@router.get('/{invoice_id}/status')
async def get_invoice_status(invoice_id: str, current_user=Depends(require_role(ALLOWED_ROLES))):
    service = EInvoiceService()
    try:
        result = await service.get_local_status(invoice_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    return std_resp(True, result.model_dump())


@router.post('/{invoice_id}/refresh-status')
async def refresh_invoice_status(invoice_id: str, current_user=Depends(require_role(ALLOWED_ROLES))):
    service = EInvoiceService()
    try:
        result = await service.refresh_status(invoice_id)
    except ProviderError as exc:
        raise HTTPException(exc.status_code, {
            'message': exc.message,
            'provider_code': exc.provider_code,
            'provider_message': exc.provider_message,
        }) from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    return std_resp(True, result.model_dump())
