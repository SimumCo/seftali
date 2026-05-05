from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from config.database import db
from utils.auth import ALGORITHM, SECRET_KEY
import jwt


class CustomerPasswordChangeGuardMiddleware(BaseHTTPMiddleware):
    ALLOWED_PATHS = {
        '/api/auth/customer/login',
        '/api/auth/customer/change-password',
    }

    async def dispatch(self, request, call_next):
        if request.url.path in self.ALLOWED_PATHS:
            return await call_next(request)

        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return await call_next(request)

        token = auth_header.split(' ', 1)[1].strip()
        if not token:
            return await call_next(request)

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except jwt.PyJWTError:
            return await call_next(request)

        if payload.get('auth_type') != 'customer_users':
            return await call_next(request)

        user_id = payload.get('sub')
        if not user_id:
            return await call_next(request)

        customer_user = await db['customer_users'].find_one({'id': user_id}, {'_id': 0})
        if not customer_user:
            return await call_next(request)

        if customer_user.get('must_change_password') is True:
            return JSONResponse(
                status_code=403,
                content={
                    'error': 'PASSWORD_CHANGE_REQUIRED',
                    'message': 'Şifre değiştirmeniz gerekiyor',
                },
            )

        return await call_next(request)
