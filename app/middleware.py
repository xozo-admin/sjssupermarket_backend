from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings
from app.core.security import decode_access_token


class ApiAuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        unsafe = request.method not in {"GET", "HEAD", "OPTIONS"}
        is_api = path.startswith(settings.api_v1_prefix)
        is_auth = path.startswith(f"{settings.api_v1_prefix}/auth/") or path.startswith(
            f"{settings.api_v1_prefix}/delivery/auth/"
        )
        if is_api and unsafe and not is_auth:
            header = request.headers.get("Authorization", "")
            payload = decode_access_token(header[7:]) if header.startswith("Bearer ") else None
            if not payload:
                return JSONResponse(
                    {"detail": "Authentication required"},
                    status_code=401,
                    headers={"WWW-Authenticate": "Bearer"},
                )
            admin_path = any(
                path.startswith(f"{settings.api_v1_prefix}/{prefix}")
                for prefix in ("catalog", "homepage", "categories")
            )
            if admin_path and payload.get("role") not in {"admin", "staff"}:
                return JSONResponse(
                    {"detail": "Administrator permission required"}, status_code=403
                )
        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(ApiAuthenticationMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
