from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials

from services.gib_import.contracts import CustomerChangePasswordPayload, CustomerLoginPayload
from services.gib_import.customer_auth_service import CustomerAuthService, CustomerLoginError
from services.seftali.core import std_resp
from utils.auth import security

router = APIRouter(prefix='/auth/customer', tags=['Customer Auth'])


@router.post('/login')
async def customer_login(body: CustomerLoginPayload):
    service = CustomerAuthService()
    try:
        result = await service.login(body.username, body.password)
    except CustomerLoginError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return std_resp(True, result)


@router.post('/change-password')
async def customer_change_password(
    body: CustomerChangePasswordPayload,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    service = CustomerAuthService()
    try:
        result = await service.change_password(credentials.credentials, body.current_password, body.new_password)
    except CustomerLoginError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc
    return result
