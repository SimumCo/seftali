import logging

from fastapi import APIRouter, Depends, HTTPException

from models.user import UserRole
from services.efatura.outbox_contracts import OutboxCreateRequest, OutboxCreateResult
from services.efatura.outbox_provider import (
    OutboxProviderError,
    TurkcellOutboxProvider,
    map_request_to_provider_body,
)
from services.gib_import.contracts import LiveGibConnectPayload, LiveGibImportPayload
from services.gib_import.errors import GibPortalError
from services.gib_import.import_service import GIBImportService
from services.gib_import.live_gib_adapter import LiveGibAdapter
from services.seftali.core import std_resp
from utils.auth import require_role

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/gib/live', tags=['GIB Live'])
SALES_ROLES = [UserRole.SALES_REP, UserRole.SALES_AGENT]
OUTBOX_ROLES = [UserRole.ADMIN, UserRole.ACCOUNTING, UserRole.SALES_AGENT, UserRole.SALES_REP]


@router.post('/connect')
async def connect_live_gib(body: LiveGibConnectPayload, current_user=Depends(require_role(SALES_ROLES))):
    adapter = LiveGibAdapter()
    try:
        result = await adapter.connect(current_user.id, body.username, body.password)
    except GibPortalError as exc:
        raise HTTPException(exc.status_code, {'code': exc.code, 'message': exc.message}) from exc
    return std_resp(True, result)


@router.post('/import/start')
async def start_live_import(body: LiveGibImportPayload, current_user=Depends(require_role(SALES_ROLES))):
    service = GIBImportService()
    try:
        result = await service.start_import(
            salesperson_id=current_user.id,
            mode='live',
            date_from=body.date_from,
            date_to=body.date_to,
        )
    except GibPortalError as exc:
        raise HTTPException(exc.status_code, {'code': exc.code, 'message': exc.message}) from exc
    return std_resp(True, result)


@router.get('/status')
async def live_status(current_user=Depends(require_role(SALES_ROLES))):
    adapter = LiveGibAdapter()
    result = await adapter.status(current_user.id)
    return std_resp(True, result)


@router.post('/disconnect')
async def disconnect_live_gib(current_user=Depends(require_role(SALES_ROLES))):
    adapter = LiveGibAdapter()
    result = await adapter.disconnect(current_user.id)
    return std_resp(True, result)


@router.post('/outbox/create', response_model=None)
async def create_outbox_invoice(
    body: OutboxCreateRequest,
    current_user=Depends(require_role(OUTBOX_ROLES)),
):
    """
    POST /api/gib/live/outbox/create

    Accepts a minimal JSON payload, maps it to the Turkcell JSON shape
    expected by POST /v1/outboxinvoice/create, and returns normalized
    { id, invoice_number, provider_status, provider_body, http_status, local_reference_id }.

    API key (`x-api-key`) is read from backend env (TURKCELL_X_API_KEY or
    legacy TURKCELL_EINVOICE_API_KEY) and never surfaced to the client or logs.
    """
    try:
        provider = TurkcellOutboxProvider()
    except OutboxProviderError as exc:
        # Config/secret missing → 500 without leaking key values
        logger.error(
            'outbox_provider_config_error',
            extra={
                'route': '/api/gib/live/outbox/create',
                'user_id': getattr(current_user, 'id', None),
                'error_code': 'provider_config_missing',
                'message': exc.message,
            },
        )
        raise HTTPException(
            status_code=500,
            detail={
                'code': 'provider_config_missing',
                'message': exc.message,
            },
        ) from exc

    # Pydantic → dict (date serialized to ISO, Decimal preserved as string via json mode)
    payload_dict = body.model_dump(mode='json')
    provider_body = map_request_to_provider_body(payload_dict)

    try:
        result = await provider.create_outbox_invoice(provider_body)
    except OutboxProviderError as exc:
        logger.warning(
            'outbox_provider_error',
            extra={
                'route': '/api/gib/live/outbox/create',
                'user_id': getattr(current_user, 'id', None),
                'provider_status': exc.status_code,
                'error_code': exc.provider_code,
                'local_reference_id': body.local_reference_id,
            },
        )
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                'code': exc.provider_code or 'provider_error',
                'message': exc.message,
                'provider_message': exc.provider_message,
                'validation_hints': exc.validation_hints,
                'raw_payload': exc.raw_payload,
            },
        ) from exc

    result_model = OutboxCreateResult(
        id=result.get('id'),
        invoice_number=result.get('invoice_number'),
        provider_status=result.get('provider_status'),
        local_reference_id=body.local_reference_id,
        http_status=result.get('http_status'),
        provider_body=result.get('provider_body') or {},
    )
    logger.info(
        'outbox_provider_success',
        extra={
            'route': '/api/gib/live/outbox/create',
            'user_id': getattr(current_user, 'id', None),
            'provider_status': result.get('http_status'),
            'local_reference_id': body.local_reference_id,
            'provider_invoice_id': result.get('id'),
        },
    )
    return std_resp(True, result_model.model_dump())
