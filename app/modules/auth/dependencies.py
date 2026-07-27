from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database.session import get_db
from app.modules.auth.model import User

bearer = HTTPBearer(auto_error=False)


async def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    payload = decode_access_token(credentials.credentials) if credentials else None
    try:
        user_id = UUID(payload["sub"]) if payload and payload.get("sub") else None
    except (ValueError, TypeError):
        user_id = None
    user = await session.get(User, user_id) if user_id else None
    if not user or not user.active:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def admin_user(user: Annotated[User, Depends(current_user)]) -> User:
    if user.role not in {"admin", "staff"}:
        raise HTTPException(status_code=403, detail="Administrator permission required")
    return user


def require_permission(permission: str):
    async def permitted(user: Annotated[User, Depends(admin_user)]) -> User:
        if (
            user.role == "admin"
            or "*" in (user.permissions or [])
            or permission in (user.permissions or [])
        ):
            return user
        raise HTTPException(status_code=403, detail=f"Permission required: {permission}")

    return permitted
