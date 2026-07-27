from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select, update
from app.modules.auth.dependencies import admin_user
from app.modules.auth.model import RefreshSession, User
from app.modules.customers.address_model import CustomerAddress
from app.modules.customers.address_router import DbSession
from app.modules.customers.admin_schemas import (
    CustomerAddressSummary,
    CustomerAdminRead,
    CustomerOrderSummary,
    CustomerStatusInput,
)
from app.modules.orders.models import Order
from app.modules.refunds.models import RefundRequest

router = APIRouter()
AdminUser = Annotated[User, Depends(admin_user)]


async def serialize_customer(session, user):
    orders = list(
        await session.scalars(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
        )
    )
    addresses = list(
        await session.scalars(
            select(CustomerAddress)
            .where(CustomerAddress.user_id == user.id)
            .order_by(CustomerAddress.is_default.desc())
        )
    )
    refunds = await session.scalar(
        select(func.count(RefundRequest.id)).where(RefundRequest.user_id == user.id)
    )
    return CustomerAdminRead(
        id=user.id,
        name=user.name,
        email=user.email,
        mobile=user.mobile,
        active=user.active,
        created_at=user.created_at,
        order_count=len(orders),
        total_spent=sum((o.total for o in orders), 0),
        refund_count=refunds or 0,
        addresses=[
            CustomerAddressSummary(
                id=a.id,
                label=", ".join(filter(None, [a.street, a.locality, a.city, a.state, a.pincode])),
                is_default=a.is_default,
            )
            for a in addresses
        ],
        recent_orders=[
            CustomerOrderSummary(id=o.id, total=o.total, status=o.status, created_at=o.created_at)
            for o in orders[:5]
        ],
    )


@router.get("", response_model=list[CustomerAdminRead])
async def list_customers(session: DbSession, user: AdminUser, search: str = "", status: str = ""):
    query = select(User).where(User.role == "customer").order_by(User.created_at.desc())
    if search.strip():
        term = f"%{search.strip()}%"
        query = query.where(
            or_(User.name.ilike(term), User.email.ilike(term), User.mobile.ilike(term))
        )
    if status == "active":
        query = query.where(User.active.is_(True))
    elif status == "inactive":
        query = query.where(User.active.is_(False))
    users = list(await session.scalars(query))
    return [await serialize_customer(session, item) for item in users]


@router.get("/{customer_id}", response_model=CustomerAdminRead)
async def get_customer(customer_id: UUID, session: DbSession, user: AdminUser):
    customer = await session.get(User, customer_id)
    if not customer or customer.role != "customer":
        raise HTTPException(404, "Customer not found")
    return await serialize_customer(session, customer)


@router.patch("/{customer_id}/status", response_model=CustomerAdminRead)
async def set_customer_status(
    customer_id: UUID, payload: CustomerStatusInput, session: DbSession, user: AdminUser
):
    customer = await session.get(User, customer_id)
    if not customer or customer.role != "customer":
        raise HTTPException(404, "Customer not found")
    customer.active = payload.active
    if not payload.active:
        await session.execute(
            update(RefreshSession).where(RefreshSession.user_id == customer.id).values(revoked=True)
        )
    await session.commit()
    await session.refresh(customer)
    return await serialize_customer(session, customer)
