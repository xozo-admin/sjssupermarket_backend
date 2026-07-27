from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from app.modules.auth.dependencies import admin_user
from app.modules.auth.model import User
from app.modules.customers.address_router import CurrentUser, DbSession
from app.modules.orders.models import Order, OrderItem
from app.modules.refunds.models import RefundConfiguration, RefundRequest
from app.modules.refunds.schemas import (
    RefundConfigInput,
    RefundConfigRead,
    RefundCreate,
    RefundDecision,
    RefundRead,
)

router = APIRouter()
AdminUser = Annotated[User, Depends(admin_user)]


async def configuration(session):
    config = await session.scalar(select(RefundConfiguration).limit(1))
    if not config:
        config = RefundConfiguration(allowed_days=7, enabled=True)
        session.add(config)
        await session.commit()
        await session.refresh(config)
    return config


async def serialize(session, refunds):
    result = []
    for refund in refunds:
        item = await session.get(OrderItem, refund.order_item_id)
        order = await session.get(Order, refund.order_id)
        user = await session.get(User, refund.user_id)
        result.append(
            RefundRead(
                id=refund.id,
                user_id=refund.user_id,
                order_id=refund.order_id,
                order_item_id=refund.order_item_id,
                customer_name=user.name if user else None,
                customer_mobile=user.mobile if user else None,
                product_name=item.product_name if item else "Product",
                amount=refund.amount,
                payment_method=order.payment_method if order else "unknown",
                reason=refund.reason,
                status=refund.status,
                admin_note=refund.admin_note,
                created_at=refund.created_at,
            )
        )
    return result


@router.get("/config", response_model=RefundConfigRead)
async def get_config(session: DbSession, user: AdminUser):
    return await configuration(session)


@router.get("/customer-config", response_model=RefundConfigRead)
async def get_customer_config(session: DbSession, user: CurrentUser):
    return await configuration(session)


@router.put("/config", response_model=RefundConfigRead)
async def update_config(payload: RefundConfigInput, session: DbSession, user: AdminUser):
    config = await configuration(session)
    config.allowed_days = payload.allowed_days
    config.enabled = payload.enabled
    await session.commit()
    await session.refresh(config)
    return config


@router.post("", response_model=RefundRead)
async def create_refund(payload: RefundCreate, session: DbSession, user: CurrentUser):
    config = await configuration(session)
    if not config.enabled:
        raise HTTPException(400, "Refund system is disabled")
    item = await session.get(OrderItem, payload.order_item_id)
    order = await session.get(Order, item.order_id) if item else None
    if not item or not order or order.user_id != user.id:
        raise HTTPException(404, "Order item not found")
    age = (datetime.now(timezone.utc) - order.created_at).days
    if age > config.allowed_days:
        raise HTTPException(400, "Refund period has expired")
    if await session.scalar(select(RefundRequest).where(RefundRequest.order_item_id == item.id)):
        raise HTTPException(409, "A refund was already requested for this item")
    refund = RefundRequest(
        user_id=user.id,
        order_id=order.id,
        order_item_id=item.id,
        reason=payload.reason.strip(),
        amount=item.line_total,
        status="pending",
    )
    session.add(refund)
    await session.commit()
    await session.refresh(refund)
    return (await serialize(session, [refund]))[0]


@router.get("/mine", response_model=list[RefundRead])
async def my_refunds(session: DbSession, user: CurrentUser):
    rows = list(
        await session.scalars(
            select(RefundRequest)
            .where(RefundRequest.user_id == user.id)
            .order_by(RefundRequest.created_at.desc())
        )
    )
    return await serialize(session, rows)


@router.get("/admin", response_model=list[RefundRead])
async def admin_refunds(session: DbSession, user: AdminUser, status: str | None = None):
    query = select(RefundRequest).order_by(RefundRequest.created_at.desc())
    if status:
        query = query.where(RefundRequest.status == status)
    return await serialize(session, list(await session.scalars(query)))


@router.patch("/admin/{refund_id}", response_model=RefundRead)
async def decide_refund(
    refund_id: UUID, payload: RefundDecision, session: DbSession, user: AdminUser
):
    refund = await session.get(RefundRequest, refund_id)
    if not refund:
        raise HTTPException(404, "Refund request not found")
    if refund.status != "pending":
        raise HTTPException(409, "Refund request has already been decided")
    refund.status = payload.status
    refund.admin_note = payload.admin_note
    await session.commit()
    await session.refresh(refund)
    return (await serialize(session, [refund]))[0]
