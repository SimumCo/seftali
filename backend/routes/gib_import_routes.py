from fastapi import APIRouter, Depends, HTTPException, Query, Response

from models.user import UserRole
from utils.auth import require_role
from services.seftali.core import std_resp
from services.gib_import.contracts import DraftCustomerApprovePayload
from services.gib_import.import_service import GIBImportService
from services.gib_import.draft_customer_service import DraftCustomerService
from services.gib_import.customer_approval_service import CustomerApprovalService, DraftApprovalError
from services.gib_import.invoice_link_service import InvoiceLinkService, InvoiceLinkError
from services.gib_import.consumption_service import CustomerConsumptionService, ConsumptionCalculationError

router = APIRouter(tags=['GIB Import'])
SALES_ROLES = [UserRole.SALES_REP, UserRole.SALES_AGENT]


@router.post('/gib/import/start')
async def start_gib_import(current_user=Depends(require_role(SALES_ROLES))):
    import_service = GIBImportService()
    draft_service = DraftCustomerService()

    import_result = await import_service.start_import(current_user.id)
    draft_result = await draft_service.aggregate_from_invoices(current_user.id)

    return std_resp(True, {
        'job': import_result,
        'draft_customers': {
            'count': draft_result['draft_customer_count'],
        },
    }, 'GIB import tamamlandı')


@router.get('/draft-customers')
async def list_draft_customers(
    salespersonId: str = Query(..., alias='salespersonId'),
    current_user=Depends(require_role(SALES_ROLES)),
):
    if salespersonId != current_user.id:
        raise HTTPException(403, 'Sadece kendi draft customer verilerinizi görüntüleyebilirsiniz')

    draft_service = DraftCustomerService()
    items = await draft_service.list_draft_customers(salespersonId)
    return std_resp(True, items)


@router.post('/draft-customers/{draft_customer_id}/approve')
async def approve_draft_customer(
    draft_customer_id: str,
    body: DraftCustomerApprovePayload,
    current_user=Depends(require_role(SALES_ROLES)),
):
    approval_service = CustomerApprovalService()
    try:
        result = await approval_service.approve(draft_customer_id, body.model_dump())
    except DraftApprovalError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return std_resp(True, result)


@router.post('/customers/{customer_id}/link-invoices')
async def link_customer_invoices(
    customer_id: str,
    current_user=Depends(require_role(SALES_ROLES)),
):
    link_service = InvoiceLinkService()
    try:
        result = await link_service.link_customer_invoices(customer_id, current_user.id)
    except InvoiceLinkError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return std_resp(True, result)


async def _run_recalculate_consumption(customer_id: str) -> dict:
    service = CustomerConsumptionService()
    try:
        return await service.recalculate(customer_id)
    except ConsumptionCalculationError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc


@router.post('/customers/{customer_id}/recalculate-consumption')
async def recalculate_customer_consumption(
    customer_id: str,
    current_user=Depends(require_role(SALES_ROLES)),
):
    """Recalculate the consumption profile for a customer (canonical route)."""
    result = await _run_recalculate_consumption(customer_id)
    return std_resp(True, result)


@router.post('/customers/{customer_id}/recalculate-consption', deprecated=True)
async def recalculate_customer_consumption_legacy(
    customer_id: str,
    response: Response,
    current_user=Depends(require_role(SALES_ROLES)),
):
    """
    DEPRECATED: use /customers/{customer_id}/recalculate-consumption instead.

    Kept for one release for backward compatibility. Emits Deprecation and Warning
    headers per RFC 8594 / RFC 7234.
    """
    import logging
    logging.getLogger(__name__).warning(
        'deprecated_route_hit',
        extra={
            'route': '/customers/{id}/recalculate-consption',
            'user_id': getattr(current_user, 'id', None),
            'replacement': '/customers/{id}/recalculate-consumption',
        },
    )
    response.headers['Deprecation'] = 'true'
    response.headers['Warning'] = '299 - "recalculate-consption is deprecated; use recalculate-consumption"'
    response.headers['Link'] = '</api/customers/{customer_id}/recalculate-consumption>; rel="successor-version"'
    result = await _run_recalculate_consumption(customer_id)
    return std_resp(True, result)


@router.get('/customers/{customer_id}/consumption')
async def get_customer_consumption(
    customer_id: str,
    current_user=Depends(require_role(SALES_ROLES)),
):
    service = CustomerConsumptionService()
    try:
        result = await service.list_consumption(customer_id)
    except ConsumptionCalculationError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return std_resp(True, result)
