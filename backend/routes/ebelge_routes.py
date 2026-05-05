"""e-Belge routes: /api/ebelge/*

Production-ready Turkcell e-Şirket entegrasyonu için additive REST katmanı.
Mevcut services/efatura (UBL v2 upload) katmanına dokunmaz.

Destekler:
    * POST /api/ebelge/efatura/create
    * GET  /api/ebelge/efatura/{id}/status
    * GET  /api/ebelge/efatura/{id}/html  (inline HTML)
    * GET  /api/ebelge/efatura/{id}/pdf   (download PDF)
    * GET  /api/ebelge/efatura/{id}/ubl   (download UBL XML)

    * POST /api/ebelge/eirsaliye/create
    * GET  /api/ebelge/eirsaliye/{id}/status
    * GET  /api/ebelge/eirsaliye/{id}/html
    * GET  /api/ebelge/eirsaliye/{id}/pdf
    * GET  /api/ebelge/eirsaliye/{id}/ubl
    * GET  /api/ebelge/eirsaliye/{id}/zip

    * GET  /api/ebelge/config/status  (admin/accounting)
    * GET  /api/ebelge/documents       (yerel ebelge_documents listesi)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from config.database import db
from middleware.auth import require_role
from models.ebelge_document import (
    EBelgeDocument,
    EBelgeDocumentType,
    EBelgeInternalStatus,
)
from models.user import User, UserRole
from schemas.ebelge_schemas import (
    EBelgeCreateResponse,
    EBelgeDocumentListItem,
    EBelgeStatusResponse,
    EFaturaCreateRequest,
    EIrsaliyeCreateRequest,
    ProviderConfigStatus,
)
from services.ebelge import (
    DocumentKind,
    TurkcellEBelgeError,
    get_api_key,
    get_base_url,
)
from services.ebelge.efatura_service import EFaturaService
from services.ebelge.eirsaliye_service import EIrsaliyeService
from services.ebelge.payload_mappers import (
    map_efatura_create_payload,
    map_eirsaliye_create_payload,
    validation_errors_for_efatura,
    validation_errors_for_eirsaliye,
)

logger = logging.getLogger("ebelge.routes")

router = APIRouter(prefix="/ebelge", tags=["e-Belge"])

# Role guard for all create/document operations.
_allowed_roles = [UserRole.ADMIN, UserRole.ACCOUNTING]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _redacted_snapshot(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Remove any sensitive-looking keys before persisting request snapshot."""
    if not isinstance(payload, dict):
        return {}
    redacted: Dict[str, Any] = {}
    for key, value in payload.items():
        lower = str(key).lower()
        if "apikey" in lower or "api_key" in lower or "authorization" in lower or "token" in lower:
            redacted[key] = "***REDACTED***"
        else:
            redacted[key] = value
    return redacted


async def _persist_document(
    *,
    document_type: EBelgeDocumentType,
    frontend_payload: Dict[str, Any],
    provider_result: Dict[str, Any],
    user: User,
    local_reference_id: Optional[str],
) -> EBelgeDocument:
    receiver = frontend_payload.get("receiver") or {}
    doc = EBelgeDocument(
        document_type=document_type,
        provider_id=provider_result.get("provider_id"),
        document_number=provider_result.get("document_number"),
        local_reference_id=local_reference_id,
        receiver_vkn=receiver.get("vkn") or receiver.get("tckn"),
        receiver_name=receiver.get("name"),
        receiver_alias=receiver.get("alias"),
        status_internal=(
            EBelgeInternalStatus.SENT if provider_result.get("success") else EBelgeInternalStatus.FAILED
        ),
        provider_status=provider_result.get("provider_status"),
        provider_message=provider_result.get("provider_message"),
        trace_id=provider_result.get("trace_id"),
        request_payload_snapshot=_redacted_snapshot(frontend_payload),
        response_payload_snapshot={
            "success": provider_result.get("success"),
            "http_status": provider_result.get("http_status"),
            "provider_id": provider_result.get("provider_id"),
            "document_number": provider_result.get("document_number"),
            "provider_status": provider_result.get("provider_status"),
            "provider_message": provider_result.get("provider_message"),
            "trace_id": provider_result.get("trace_id"),
            "raw_provider_body": provider_result.get("raw_provider_body"),
        },
        created_by=user.id,
        created_by_username=user.username,
    )

    to_insert = doc.model_dump()
    for key in ("created_at", "updated_at"):
        value = to_insert.get(key)
        if isinstance(value, datetime):
            to_insert[key] = value.isoformat()

    await db.ebelge_documents.insert_one(to_insert)
    return doc


async def _persist_failed_attempt(
    *,
    document_type: EBelgeDocumentType,
    frontend_payload: Dict[str, Any],
    err: TurkcellEBelgeError,
    user: User,
    local_reference_id: Optional[str],
) -> None:
    receiver = frontend_payload.get("receiver") or {}
    doc = EBelgeDocument(
        document_type=document_type,
        local_reference_id=local_reference_id,
        receiver_vkn=receiver.get("vkn") or receiver.get("tckn"),
        receiver_name=receiver.get("name"),
        receiver_alias=receiver.get("alias"),
        status_internal=EBelgeInternalStatus.FAILED,
        provider_status=err.provider_status,
        provider_message=err.message,
        trace_id=err.trace_id,
        request_payload_snapshot=_redacted_snapshot(frontend_payload),
        response_payload_snapshot={
            "success": False,
            "http_status": err.status_code,
            "provider_status": err.provider_status,
            "provider_message": err.message,
            "trace_id": err.trace_id,
            "raw_provider_body": err.provider_body,
        },
        created_by=user.id,
        created_by_username=user.username,
    )

    to_insert = doc.model_dump()
    for key in ("created_at", "updated_at"):
        value = to_insert.get(key)
        if isinstance(value, datetime):
            to_insert[key] = value.isoformat()

    try:
        await db.ebelge_documents.insert_one(to_insert)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to persist failed ebelge attempt: %s", exc)


def _handle_provider_error(err: TurkcellEBelgeError) -> HTTPException:
    """Translate TurkcellEBelgeError into an HTTPException (never leaks secrets)."""
    payload: Dict[str, Any] = {
        "message": err.message,
        "provider_status": err.provider_status,
        "trace_id": err.trace_id,
    }
    if err.provider_body is not None:
        # Trim large bodies to keep responses small.
        body = err.provider_body
        if isinstance(body, str) and len(body) > 1000:
            body = body[:1000] + "...[truncated]"
        payload["provider_body"] = body

    status_code = err.status_code if 400 <= err.status_code < 600 else 502
    return HTTPException(status_code=status_code, detail=payload)


# ---------------------------------------------------------------------------
# CONFIG status
# ---------------------------------------------------------------------------

@router.get("/config/status", response_model=ProviderConfigStatus)
async def config_status(current_user: User = Depends(require_role(_allowed_roles))):
    import os

    api_key = get_api_key()
    env_flag = (os.environ.get("TURKCELL_EBELGE_ENV") or "test").strip().lower()
    efatura_base = get_base_url(DocumentKind.EFATURA)
    eirsaliye_base = get_base_url(DocumentKind.EIRSALIYE)
    has_legacy = bool(
        os.environ.get("TURKCELL_EINVOICE_API_KEY") or os.environ.get("TURKCELL_X_API_KEY")
    )
    return ProviderConfigStatus(
        api_key_configured=bool(api_key),
        environment="prod" if env_flag in {"prod", "production", "live"} else "test",
        efatura_base_url=efatura_base,
        eirsaliye_base_url=eirsaliye_base,
        has_legacy_fallback=has_legacy,
    )


# ---------------------------------------------------------------------------
# e-FATURA
# ---------------------------------------------------------------------------

@router.post("/efatura/create", response_model=EBelgeCreateResponse)
async def efatura_create(
    payload: EFaturaCreateRequest,
    current_user: User = Depends(require_role(_allowed_roles)),
):
    frontend_payload = payload.model_dump()
    validation_errors = validation_errors_for_efatura(frontend_payload)
    if validation_errors:
        raise HTTPException(status_code=422, detail={"message": "Validation failed", "errors": validation_errors})

    provider_payload = map_efatura_create_payload(frontend_payload)
    local_reference_id = provider_payload.get("localReferenceId")

    try:
        service = EFaturaService()
        provider_result = service.create(provider_payload)
    except TurkcellEBelgeError as err:
        await _persist_failed_attempt(
            document_type=EBelgeDocumentType.EFATURA,
            frontend_payload=frontend_payload,
            err=err,
            user=current_user,
            local_reference_id=local_reference_id,
        )
        raise _handle_provider_error(err)

    doc = await _persist_document(
        document_type=EBelgeDocumentType.EFATURA,
        frontend_payload=frontend_payload,
        provider_result=provider_result,
        user=current_user,
        local_reference_id=local_reference_id,
    )

    return EBelgeCreateResponse(
        id=doc.id,
        document_type=EBelgeDocumentType.EFATURA.value,
        provider_id=provider_result.get("provider_id"),
        document_number=provider_result.get("document_number"),
        provider_status=provider_result.get("provider_status"),
        provider_message=provider_result.get("provider_message"),
        local_reference_id=local_reference_id,
        status_internal=doc.status_internal.value,
        trace_id=provider_result.get("trace_id"),
        raw_provider_body=provider_result.get("raw_provider_body"),
    )


@router.get("/efatura/{provider_id}/status", response_model=EBelgeStatusResponse)
async def efatura_status(
    provider_id: str,
    current_user: User = Depends(require_role(_allowed_roles)),
):
    try:
        service = EFaturaService()
        result = service.status(provider_id)
    except TurkcellEBelgeError as err:
        raise _handle_provider_error(err)

    return EBelgeStatusResponse(
        provider_id=provider_id,
        document_type=EBelgeDocumentType.EFATURA.value,
        success=True,
        provider_status=result.get("provider_status"),
        provider_message=result.get("provider_message"),
        raw_provider_body=result.get("raw_provider_body"),
    )


@router.get("/efatura/{provider_id}/html")
async def efatura_html(
    provider_id: str,
    is_standart_xslt: bool = Query(True, alias="isStandartXslt"),
    current_user: User = Depends(require_role(_allowed_roles)),
):
    try:
        service = EFaturaService()
        result = service.html(provider_id, is_standart_xslt)
    except TurkcellEBelgeError as err:
        raise _handle_provider_error(err)
    return Response(content=result["content"], media_type=result.get("content_type", "text/html"))


@router.get("/efatura/{provider_id}/pdf")
async def efatura_pdf(
    provider_id: str,
    is_standart_xslt: bool = Query(True, alias="isStandartXslt"),
    current_user: User = Depends(require_role(_allowed_roles)),
):
    try:
        service = EFaturaService()
        result = service.pdf(provider_id, is_standart_xslt)
    except TurkcellEBelgeError as err:
        raise _handle_provider_error(err)
    return Response(
        content=result["content"],
        media_type=result.get("content_type", "application/pdf"),
        headers={"Content-Disposition": f'attachment; filename="efatura-{provider_id}.pdf"'},
    )


@router.get("/efatura/{provider_id}/ubl")
async def efatura_ubl(
    provider_id: str,
    current_user: User = Depends(require_role(_allowed_roles)),
):
    try:
        service = EFaturaService()
        result = service.ubl(provider_id)
    except TurkcellEBelgeError as err:
        raise _handle_provider_error(err)
    return Response(
        content=result["content"],
        media_type=result.get("content_type", "application/xml"),
        headers={"Content-Disposition": f'attachment; filename="efatura-{provider_id}.xml"'},
    )


# ---------------------------------------------------------------------------
# e-İRSALİYE
# ---------------------------------------------------------------------------

@router.post("/eirsaliye/create", response_model=EBelgeCreateResponse)
async def eirsaliye_create(
    payload: EIrsaliyeCreateRequest,
    current_user: User = Depends(require_role(_allowed_roles)),
):
    frontend_payload = payload.model_dump()
    validation_errors = validation_errors_for_eirsaliye(frontend_payload)
    if validation_errors:
        raise HTTPException(status_code=422, detail={"message": "Validation failed", "errors": validation_errors})

    provider_payload = map_eirsaliye_create_payload(frontend_payload)
    local_reference_id = provider_payload.get("localReferenceId")

    try:
        service = EIrsaliyeService()
        provider_result = service.create(provider_payload)
    except TurkcellEBelgeError as err:
        await _persist_failed_attempt(
            document_type=EBelgeDocumentType.EIRSALIYE,
            frontend_payload=frontend_payload,
            err=err,
            user=current_user,
            local_reference_id=local_reference_id,
        )
        raise _handle_provider_error(err)

    doc = await _persist_document(
        document_type=EBelgeDocumentType.EIRSALIYE,
        frontend_payload=frontend_payload,
        provider_result=provider_result,
        user=current_user,
        local_reference_id=local_reference_id,
    )

    return EBelgeCreateResponse(
        id=doc.id,
        document_type=EBelgeDocumentType.EIRSALIYE.value,
        provider_id=provider_result.get("provider_id"),
        document_number=provider_result.get("document_number"),
        provider_status=provider_result.get("provider_status"),
        provider_message=provider_result.get("provider_message"),
        local_reference_id=local_reference_id,
        status_internal=doc.status_internal.value,
        trace_id=provider_result.get("trace_id"),
        raw_provider_body=provider_result.get("raw_provider_body"),
    )


@router.get("/eirsaliye/{provider_id}/status", response_model=EBelgeStatusResponse)
async def eirsaliye_status(
    provider_id: str,
    current_user: User = Depends(require_role(_allowed_roles)),
):
    try:
        service = EIrsaliyeService()
        result = service.status(provider_id)
    except TurkcellEBelgeError as err:
        raise _handle_provider_error(err)

    return EBelgeStatusResponse(
        provider_id=provider_id,
        document_type=EBelgeDocumentType.EIRSALIYE.value,
        success=True,
        provider_status=result.get("provider_status"),
        provider_message=result.get("provider_message"),
        raw_provider_body=result.get("raw_provider_body"),
    )


@router.get("/eirsaliye/{provider_id}/html")
async def eirsaliye_html(
    provider_id: str,
    is_standart_xslt: bool = Query(True, alias="isStandartXslt"),
    current_user: User = Depends(require_role(_allowed_roles)),
):
    try:
        service = EIrsaliyeService()
        result = service.html(provider_id, is_standart_xslt)
    except TurkcellEBelgeError as err:
        raise _handle_provider_error(err)
    return Response(content=result["content"], media_type=result.get("content_type", "text/html"))


@router.get("/eirsaliye/{provider_id}/pdf")
async def eirsaliye_pdf(
    provider_id: str,
    is_standart_xslt: bool = Query(True, alias="isStandartXslt"),
    current_user: User = Depends(require_role(_allowed_roles)),
):
    try:
        service = EIrsaliyeService()
        result = service.pdf(provider_id, is_standart_xslt)
    except TurkcellEBelgeError as err:
        raise _handle_provider_error(err)
    return Response(
        content=result["content"],
        media_type=result.get("content_type", "application/pdf"),
        headers={"Content-Disposition": f'attachment; filename="eirsaliye-{provider_id}.pdf"'},
    )


@router.get("/eirsaliye/{provider_id}/ubl")
async def eirsaliye_ubl(
    provider_id: str,
    current_user: User = Depends(require_role(_allowed_roles)),
):
    try:
        service = EIrsaliyeService()
        result = service.ubl(provider_id)
    except TurkcellEBelgeError as err:
        raise _handle_provider_error(err)
    return Response(
        content=result["content"],
        media_type=result.get("content_type", "application/xml"),
        headers={"Content-Disposition": f'attachment; filename="eirsaliye-{provider_id}.xml"'},
    )


@router.get("/eirsaliye/{provider_id}/zip")
async def eirsaliye_zip(
    provider_id: str,
    current_user: User = Depends(require_role(_allowed_roles)),
):
    try:
        service = EIrsaliyeService()
        result = service.zip(provider_id)
    except TurkcellEBelgeError as err:
        raise _handle_provider_error(err)
    return Response(
        content=result["content"],
        media_type=result.get("content_type", "application/zip"),
        headers={"Content-Disposition": f'attachment; filename="eirsaliye-{provider_id}.zip"'},
    )


# ---------------------------------------------------------------------------
# Local document listing
# ---------------------------------------------------------------------------

@router.get("/documents", response_model=List[EBelgeDocumentListItem])
async def list_documents(
    document_type: Optional[str] = Query(None, description="efatura | eirsaliye"),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(require_role(_allowed_roles)),
):
    query: Dict[str, Any] = {}
    if document_type:
        if document_type not in ("efatura", "eirsaliye"):
            raise HTTPException(status_code=422, detail="Invalid document_type")
        query["document_type"] = document_type

    items: List[EBelgeDocumentListItem] = []
    async for doc in db.ebelge_documents.find(query, {"_id": 0}).sort("created_at", -1).limit(limit):
        created_at = doc.get("created_at")
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()
        items.append(
            EBelgeDocumentListItem(
                id=doc.get("id"),
                document_type=doc.get("document_type"),
                provider_id=doc.get("provider_id"),
                document_number=doc.get("document_number"),
                receiver_name=doc.get("receiver_name"),
                receiver_vkn=doc.get("receiver_vkn"),
                status_internal=doc.get("status_internal") or "unknown",
                provider_status=doc.get("provider_status"),
                created_at=str(created_at) if created_at else "",
                created_by_username=doc.get("created_by_username"),
            )
        )
    return items
