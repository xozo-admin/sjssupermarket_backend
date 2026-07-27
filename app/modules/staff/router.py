from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import or_, select
from app.core.security import hash_password
from app.modules.auth.dependencies import current_user
from app.modules.auth.model import User
from app.modules.customers.address_router import DbSession

router = APIRouter()
PERMISSIONS = [
    "dashboard.view",
    "catalog.manage",
    "orders.manage",
    "pos.manage",
    "suppliers.manage",
    "customers.manage",
    "delivery.manage",
    "reports.view",
    "staff.manage",
    "settings.manage",
]


async def super_admin(user: Annotated[User, Depends(current_user)]):
    if user.role != "admin":
        raise HTTPException(403, "Super administrator permission required")
    return user


class StaffInput(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    mobile: str | None = None
    designation: str = Field(default="Staff", max_length=100)
    permissions: list[str] = []
    password: str | None = Field(default=None, min_length=8, max_length=128)
    active: bool = True


class PasswordInput(BaseModel):
    password: str = Field(min_length=8, max_length=128)


def read(u: User):
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "mobile": u.mobile,
        "designation": u.designation,
        "permissions": u.permissions or [],
        "active": u.active,
        "created_at": u.created_at,
    }


@router.get("")
async def list_staff(session: DbSession, _: User = Depends(super_admin)):
    return [
        read(u)
        for u in await session.scalars(
            select(User).where(User.role == "staff").order_by(User.created_at.desc())
        )
    ]


@router.get("/permissions")
async def permissions(_: User = Depends(super_admin)):
    return PERMISSIONS


@router.post("")
async def create_staff(p: StaffInput, session: DbSession, _: User = Depends(super_admin)):
    if not p.password:
        raise HTTPException(400, "Password is required for new staff")
    if await session.scalar(
        select(User).where(
            or_(User.email == p.email.lower(), User.mobile == p.mobile)
            if p.mobile
            else User.email == p.email.lower()
        )
    ):
        raise HTTPException(409, "Email or mobile already exists")
    invalid = set(p.permissions) - set(PERMISSIONS)
    if invalid:
        raise HTTPException(400, f"Unknown permissions: {', '.join(invalid)}")
    u = User(
        name=p.name.strip(),
        email=p.email.lower(),
        mobile=p.mobile,
        password_hash=hash_password(p.password),
        role="staff",
        active=p.active,
        designation=p.designation,
        permissions=p.permissions,
    )
    session.add(u)
    await session.commit()
    await session.refresh(u)
    return read(u)


@router.put("/{staff_id}")
async def update_staff(
    staff_id: UUID, p: StaffInput, session: DbSession, _: User = Depends(super_admin)
):
    u = await session.get(User, staff_id)
    if not u or u.role != "staff":
        raise HTTPException(404, "Staff account not found")
    invalid = set(p.permissions) - set(PERMISSIONS)
    if invalid:
        raise HTTPException(400, "Unknown permissions")
    u.name = p.name.strip()
    u.email = p.email.lower()
    u.mobile = p.mobile
    u.designation = p.designation
    u.permissions = p.permissions
    u.active = p.active
    if p.password:
        u.password_hash = hash_password(p.password)
    await session.commit()
    await session.refresh(u)
    return read(u)


@router.patch("/{staff_id}/password")
async def reset_password(
    staff_id: UUID, p: PasswordInput, session: DbSession, _: User = Depends(super_admin)
):
    u = await session.get(User, staff_id)
    if not u or u.role != "staff":
        raise HTTPException(404, "Staff account not found")
    u.password_hash = hash_password(p.password)
    await session.commit()
    return {"message": "Password updated"}
