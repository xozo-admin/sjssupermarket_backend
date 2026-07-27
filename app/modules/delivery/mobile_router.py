from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from app.core.security import create_access_token, decode_access_token, verify_password
from app.database.session import get_db
from app.modules.auth.dependencies import bearer
from app.modules.delivery.models import (
    DeliveryActivity,
    DeliveryAttendance,
    DeliveryEarning,
    DeliveryLeave,
    DeliveryMan,
    DeliveryNotification,
)
from app.modules.delivery.schemas import DeliveryRead
from app.modules.orders.models import Order
from app.modules.orders.router import serialize_orders
from app.modules.notifications.models import PushDevice
from app.modules.notifications.firebase import send_push
from app.modules.notifications.schemas import DeviceRegistration
from app.realtime.delivery import delivery_sockets

router = APIRouter()
DbSession = Annotated[object, Depends(get_db)]


class DeliveryLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AvailabilityUpdate(BaseModel):
    online: bool | None = None
    delivery_status: str | None = Field(
        default=None,
        pattern="^(available|offline)$",
    )
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class OrderStatusUpdate(BaseModel):
    status: str = Field(pattern="^(accepted|picked_up|on_the_way|delivered|rejected|failed)$")
    delivery_otp: str | None = Field(default=None, min_length=6, max_length=6)
    cod_collected: bool = False
    proof_url: str | None = Field(default=None, max_length=500)


class LeaveRequest(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(min_length=5, max_length=1000)


async def current_delivery_man(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session=Depends(get_db),
) -> DeliveryMan:
    payload = decode_access_token(credentials.credentials) if credentials else None
    try:
        man_id = UUID(payload["sub"]) if payload and payload.get("role") == "delivery" else None
    except (ValueError, TypeError):
        man_id = None
    man = await session.get(DeliveryMan, man_id) if man_id else None
    if not man or not man.active or man.blocked:
        raise HTTPException(
            status_code=401,
            detail="Delivery partner authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return man


DeliveryPartner = Annotated[DeliveryMan, Depends(current_delivery_man)]


async def log(session, man_id: UUID, action: str, details: str | None = None):
    session.add(
        DeliveryActivity(
            delivery_man_id=man_id,
            action=action,
            details=details,
        )
    )


async def profile_data(session, man: DeliveryMan) -> dict:
    active_order = await session.scalar(
        select(Order.id)
        .where(
            Order.delivery_man_id == man.id,
            Order.status.notin_(["delivered", "cancelled", "failed"]),
        )
        .limit(1)
    )
    data = DeliveryRead.model_validate(man).model_dump()
    data["active_order_id"] = active_order
    return data


async def delivery_order_data(session, orders: list[Order]) -> list[dict]:
    values = await serialize_orders(session, orders)
    for value in values:
        value.pop("delivery_otp", None)
    return values


@router.post("/auth/login")
async def login(payload: DeliveryLogin, session=Depends(get_db)):
    man = await session.scalar(
        select(DeliveryMan).where(DeliveryMan.email == payload.email.strip().lower())
    )
    if not man or not verify_password(payload.password, man.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not man.active or man.blocked:
        raise HTTPException(status_code=403, detail="This delivery account is disabled")
    if man.verification_status != "verified":
        raise HTTPException(
            status_code=403,
            detail="Your delivery account is awaiting verification",
        )
    await log(session, man.id, "login")
    await session.commit()
    return {
        "access_token": create_access_token(
            str(man.id),
            expires_minutes=60 * 24 * 7,
            role="delivery",
        ),
        "token_type": "bearer",
        "delivery_man": await profile_data(session, man),
    }


@router.get("/me")
async def me(man: DeliveryPartner, session=Depends(get_db)):
    return await profile_data(session, man)


@router.patch("/me/availability")
async def update_availability(
    payload: AvailabilityUpdate,
    man: DeliveryPartner,
    session=Depends(get_db),
):
    was_online = man.online
    if payload.online is not None:
        man.online = payload.online
        man.delivery_status = "available" if payload.online else "offline"
    if payload.delivery_status is not None:
        man.delivery_status = payload.delivery_status
        man.online = payload.delivery_status != "offline"
    if payload.latitude is not None:
        man.latitude = payload.latitude
    if payload.longitude is not None:
        man.longitude = payload.longitude
    man.last_active_at = datetime.now(timezone.utc)
    if man.online and not was_online:
        session.add(
            DeliveryAttendance(
                delivery_man_id=man.id,
                login_at=datetime.now(timezone.utc),
            )
        )
        await log(session, man.id, "online")
    elif was_online and not man.online:
        attendance = await session.scalar(
            select(DeliveryAttendance)
            .where(
                DeliveryAttendance.delivery_man_id == man.id,
                DeliveryAttendance.logout_at.is_(None),
            )
            .order_by(DeliveryAttendance.login_at.desc())
            .limit(1)
        )
        if attendance:
            attendance.logout_at = datetime.now(timezone.utc)
            attendance.online_minutes = max(
                0,
                int((attendance.logout_at - attendance.login_at).total_seconds() / 60),
            )
        await log(session, man.id, "offline")
    await session.commit()
    await session.refresh(man)
    await delivery_sockets.to_admins(
        "availability_updated",
        {"delivery_man_id": str(man.id), "online": man.online, "status": man.delivery_status},
    )
    if payload.latitude is not None or payload.longitude is not None:
        active_orders = list(
            await session.scalars(
                select(Order).where(
                    Order.delivery_man_id == man.id,
                    Order.status.notin_(["delivered", "cancelled", "failed"]),
                )
            )
        )
        for active_order in active_orders:
            await delivery_sockets.to_customer(
                active_order.user_id,
                "location_updated",
                {
                    "order_id": str(active_order.id),
                    "latitude": man.latitude,
                    "longitude": man.longitude,
                    "status": active_order.status,
                },
            )
    return await profile_data(session, man)


@router.get("/dashboard")
async def dashboard(man: DeliveryPartner, session=Depends(get_db)):
    today = date.today()
    today_deliveries = await session.scalar(
        select(func.count(Order.id)).where(
            Order.delivery_man_id == man.id,
            Order.status == "delivered",
            func.date(Order.updated_at) == today,
        )
    )
    today_earnings = await session.scalar(
        select(func.coalesce(func.sum(DeliveryEarning.amount), 0)).where(
            DeliveryEarning.delivery_man_id == man.id,
            func.date(DeliveryEarning.created_at) == today,
        )
    )
    active_orders = await session.scalar(
        select(func.count(Order.id)).where(
            Order.delivery_man_id == man.id,
            Order.status.notin_(["delivered", "cancelled", "failed"]),
        )
    )
    return {
        "online": man.online,
        "delivery_status": man.delivery_status,
        "active_orders": active_orders or 0,
        "today_deliveries": today_deliveries or 0,
        "today_earnings": today_earnings or 0,
        "total_deliveries": man.total_deliveries,
        "completed_orders": man.completed_orders,
        "rating": man.rating,
        "average_delivery_minutes": man.average_delivery_minutes,
    }


@router.get("/orders")
async def orders(
    man: DeliveryPartner,
    session=Depends(get_db),
    history: bool = Query(default=False),
):
    query = select(Order).where(Order.delivery_man_id == man.id)
    if history:
        query = query.where(Order.status.in_(["delivered", "cancelled", "failed"]))
    else:
        query = query.where(Order.status.notin_(["delivered", "cancelled", "failed"]))
    values = list(await session.scalars(query.order_by(Order.created_at.desc())))
    return await delivery_order_data(session, values)


@router.get("/orders/{order_id}")
async def order_detail(
    order_id: UUID,
    man: DeliveryPartner,
    session=Depends(get_db),
):
    order = await session.scalar(
        select(Order).where(Order.id == order_id, Order.delivery_man_id == man.id)
    )
    if not order:
        raise HTTPException(status_code=404, detail="Assigned order not found")
    return (await delivery_order_data(session, [order]))[0]


@router.patch("/orders/{order_id}/status")
async def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    man: DeliveryPartner,
    session=Depends(get_db),
):
    order = await session.scalar(
        select(Order).where(Order.id == order_id, Order.delivery_man_id == man.id).with_for_update()
    )
    if not order:
        raise HTTPException(status_code=404, detail="Assigned order not found")
    transitions = {
        "assigned": {"accepted", "rejected"},
        "accepted": {"picked_up", "rejected"},
        "picked_up": {"on_the_way", "failed"},
        "on_the_way": {"delivered", "failed"},
    }
    if payload.status not in transitions.get(order.status, set()):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change order from {order.status} to {payload.status}",
        )
    if payload.status == "delivered":
        if not order.delivery_otp or payload.delivery_otp != order.delivery_otp:
            raise HTTPException(status_code=409, detail="Incorrect delivery OTP")
        if order.payment_method == "cod" and not payload.cod_collected:
            raise HTTPException(status_code=409, detail="Confirm COD collection before delivery")
        order.cod_collected = payload.cod_collected
        order.payment_status = "paid" if payload.cod_collected else order.payment_status
        order.delivery_proof_url = payload.proof_url
        order.delivered_at = datetime.now(timezone.utc)
    if payload.status == "rejected":
        order.delivery_man_id = None
        order.status = "placed"
        man.delivery_status = "available" if man.online else "offline"
        await log(session, man.id, "order_rejected", str(order.id))
        await session.commit()
        await delivery_sockets.to_admins(
            "order_rejected", {"delivery_man_id": str(man.id), "order_id": str(order.id)}
        )
        await delivery_sockets.to_customer(
            order.user_id, "order_status_updated", {"order_id": str(order.id), "status": "placed"}
        )
        return {"ok": True, "status": "placed"}
    order.status = payload.status
    man.delivery_status = payload.status
    if payload.status in {"delivered", "cancelled", "failed"}:
        man.delivery_status = "available" if man.online else "offline"
    if payload.status == "delivered":
        man.total_deliveries += 1
        man.completed_orders += 1
        existing = await session.scalar(
            select(DeliveryEarning.id).where(DeliveryEarning.order_id == order.id)
        )
        if not existing:
            session.add(
                DeliveryEarning(
                    delivery_man_id=man.id,
                    order_id=order.id,
                    amount=order.delivery_fee,
                    cash_collected=order.total if order.payment_method == "cod" else Decimal("0"),
                    online_payment=order.total if order.payment_method != "cod" else Decimal("0"),
                )
            )
    elif payload.status == "cancelled":
        man.cancelled_orders += 1
    elif payload.status == "failed":
        man.failed_orders += 1
    await log(session, man.id, f"order_{payload.status}", str(order.id))
    await session.commit()
    customer_tokens = list(
        await session.scalars(
            select(PushDevice.token).where(
                PushDevice.user_id == order.user_id, PushDevice.active.is_(True)
            )
        )
    )
    customer_title = {
        "accepted": "Order accepted",
        "picked_up": "Order picked up",
        "on_the_way": "Order is on the way",
        "delivered": "Order delivered",
        "failed": "Delivery failed",
    }.get(order.status, "Order updated")
    await send_push(
        customer_tokens,
        customer_title,
        f"Order #{str(order.id)[:8].upper()} is now {order.status.replace('_', ' ')}",
        {
            "type": "order_status",
            "order_id": str(order.id),
            "status": order.status,
            "route": "orders",
        },
    )
    await delivery_sockets.to_delivery(
        man.id,
        "order_status_updated",
        {"order_id": str(order.id), "status": order.status},
    )
    await delivery_sockets.to_admins(
        "order_status_updated",
        {"delivery_man_id": str(man.id), "order_id": str(order.id), "status": order.status},
    )
    await delivery_sockets.to_customer(
        order.user_id,
        "order_status_updated",
        {
            "order_id": str(order.id),
            "status": order.status,
            "latitude": man.latitude,
            "longitude": man.longitude,
        },
    )
    return {"ok": True, "status": order.status}


@router.get("/attendance")
async def attendance(man: DeliveryPartner, session=Depends(get_db)):
    return list(
        await session.scalars(
            select(DeliveryAttendance)
            .where(DeliveryAttendance.delivery_man_id == man.id)
            .order_by(DeliveryAttendance.login_at.desc())
            .limit(90)
        )
    )


@router.get("/earnings")
async def earnings(man: DeliveryPartner, session=Depends(get_db)):
    entries = list(
        await session.scalars(
            select(DeliveryEarning)
            .where(DeliveryEarning.delivery_man_id == man.id)
            .order_by(DeliveryEarning.created_at.desc())
            .limit(200)
        )
    )
    return {
        "total": sum((entry.amount for entry in entries), Decimal("0")),
        "cash_collected": sum((entry.cash_collected for entry in entries), Decimal("0")),
        "online_payments": sum((entry.online_payment for entry in entries), Decimal("0")),
        "pending_settlement": sum(
            (entry.amount for entry in entries if entry.settlement_status == "pending"),
            Decimal("0"),
        ),
        "entries": entries,
    }


@router.get("/leaves")
async def leaves(man: DeliveryPartner, session=Depends(get_db)):
    return list(
        await session.scalars(
            select(DeliveryLeave)
            .where(DeliveryLeave.delivery_man_id == man.id)
            .order_by(DeliveryLeave.created_at.desc())
        )
    )


@router.post("/leaves", status_code=status.HTTP_201_CREATED)
async def request_leave(
    payload: LeaveRequest,
    man: DeliveryPartner,
    session=Depends(get_db),
):
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="End date must follow start date")
    leave = DeliveryLeave(delivery_man_id=man.id, **payload.model_dump())
    session.add(leave)
    await log(session, man.id, "leave_requested", payload.reason)
    await session.commit()
    await session.refresh(leave)
    return leave


@router.get("/notifications")
async def notifications(man: DeliveryPartner, session=Depends(get_db)):
    return list(
        await session.scalars(
            select(DeliveryNotification)
            .where(
                (DeliveryNotification.delivery_man_id == man.id)
                | (DeliveryNotification.delivery_man_id.is_(None))
            )
            .order_by(DeliveryNotification.created_at.desc())
            .limit(100)
        )
    )


@router.post("/devices", status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceRegistration,
    man: DeliveryPartner,
    session=Depends(get_db),
):
    device = await session.scalar(select(PushDevice).where(PushDevice.token == payload.token))
    if device is None:
        device = PushDevice(token=payload.token, platform=payload.platform, app_kind="delivery")
        session.add(device)
    device.platform = payload.platform
    device.app_kind = "delivery"
    device.delivery_man_id = man.id
    device.user_id = None
    device.active = True
    await session.commit()
    return {"ok": True}
