from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.database.session import get_db
from app.modules.auth.dependencies import current_user
from app.modules.auth.model import RefreshSession, User
from app.modules.auth.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
)

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


def token_hash(token: str) -> str:
    return sha256(token.encode()).hexdigest()


async def issue_session(session: AsyncSession, user: User) -> TokenResponse:
    refresh_token = token_urlsafe(48)
    session.add(
        RefreshSession(
            user_id=user.id,
            token_hash=token_hash(refresh_token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
    )
    await session.commit()
    return TokenResponse(
        access_token=create_access_token(str(user.id), role=user.role),
        refresh_token=refresh_token,
        user=user,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: RegisterRequest, session: DbSession):
    duplicate = await session.scalar(
        select(User).where(
            or_(User.email == payload.email, User.mobile == payload.mobile)
            if payload.mobile
            else User.email == payload.email
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="An account with these details already exists")
    user = User(
        name=payload.name.strip(),
        email=payload.email,
        mobile=payload.mobile,
        password_hash=hash_password(payload.password),
        role="customer",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return await issue_session(session, user)


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest, session: DbSession):
    user = await session.scalar(select(User).where(User.email == payload.email.strip().lower()))
    if not user or not verify_password(payload.password, user.password_hash) or not user.active:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return await issue_session(session, user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(payload: RefreshRequest, session: DbSession):
    stored = await session.scalar(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_hash(payload.refresh_token),
            RefreshSession.revoked.is_(False),
        )
    )
    if not stored or stored.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    user = await session.get(User, stored.user_id)
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="Authentication required")
    stored.revoked = True
    await session.flush()
    return await issue_session(session, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(payload: RefreshRequest, session: DbSession):
    stored = await session.scalar(
        select(RefreshSession).where(RefreshSession.token_hash == token_hash(payload.refresh_token))
    )
    if stored:
        stored.revoked = True
        await session.commit()


@router.get("/me", response_model=UserRead)
async def me(user: Annotated[User, Depends(current_user)]):
    return user
