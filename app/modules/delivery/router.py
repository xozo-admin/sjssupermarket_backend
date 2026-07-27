from datetime import datetime, timezone, date
import secrets
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, or_, select
from app.modules.auth.dependencies import admin_user
from app.modules.auth.model import User
from app.modules.auth.router import DbSession
from app.core.security import hash_password
from app.modules.delivery.models import (
    DeliveryActivity,
    DeliveryAttendance,
    DeliveryEarning,
    DeliveryLeave,
    DeliveryMan,
    DeliveryNotification,
)
from app.modules.delivery.schemas import (
    AssignInput,
    DeliveryInput,
    DeliveryPatch,
    DeliveryRead,
    LeaveDecision,
    NotificationInput,
    ResetPasswordInput,
)
from app.modules.orders.models import Order
from app.modules.notifications.firebase import send_push
from app.modules.notifications.models import PushDevice
from app.realtime.delivery import delivery_sockets

router = APIRouter()
AdminUser = Annotated[User, Depends(admin_user)]


async def log(session, man_id, action, details=None):
    session.add(DeliveryActivity(delivery_man_id=man_id, action=action, details=details))


async def serialize(session, man):
    active = await session.scalar(
        select(Order.id)
        .where(Order.delivery_man_id == man.id, Order.status.notin_(["delivered", "cancelled"]))
        .limit(1)
    )
    data = DeliveryRead.model_validate(man).model_dump()
    data["active_order_id"] = active
    return data


@router.get("/dashboard")
async def dashboard(session: DbSession, user: AdminUser):
    men = list(await session.scalars(select(DeliveryMan)))
    today = date.today()
    earn = await session.scalar(
        select(func.coalesce(func.sum(DeliveryEarning.amount), 0)).where(
            func.date(DeliveryEarning.created_at) == today
        )
    )
    deliveries = await session.scalar(
        select(func.count(Order.id)).where(
            func.date(Order.updated_at) == today, Order.status == "delivered"
        )
    )
    return {
        "total": len(men),
        "active": sum(m.active for m in men),
        "offline": sum(not m.online for m in men),
        "available": sum(m.delivery_status == "available" for m in men),
        "on_delivery": sum(
            m.delivery_status in {"assigned", "accepted", "picked_up", "on_the_way"} for m in men
        ),
        "pending_verification": sum(m.verification_status == "pending" for m in men),
        "blocked": sum(m.blocked for m in men),
        "today_deliveries": deliveries or 0,
        "today_earnings": earn,
        "average_rating": sum(m.rating for m in men) / len(men) if men else 0,
    }


@router.get("", response_model=list[DeliveryRead])
async def list_men(
    session: DbSession,
    user: AdminUser,
    search: str = "",
    status: str = "",
    zone: str = "",
    online: str = "",
    vehicle_type: str = "",
):
    q = select(DeliveryMan).order_by(DeliveryMan.created_at.desc())
    term = f"%{search.strip()}%"
    if search.strip():
        q = q.where(
            or_(
                DeliveryMan.name.ilike(term),
                DeliveryMan.mobile.ilike(term),
                DeliveryMan.email.ilike(term),
            )
        )
    if status:
        q = q.where(DeliveryMan.delivery_status == status)
    if zone:
        q = q.where(DeliveryMan.zone == zone)
    if online in {"true", "false"}:
        q = q.where(DeliveryMan.online.is_(online == "true"))
    if vehicle_type:
        q = q.where(DeliveryMan.vehicle_type == vehicle_type)
    return [await serialize(session, m) for m in list(await session.scalars(q))]


@router.post("", response_model=DeliveryRead, status_code=201)
async def create(payload: DeliveryInput, session: DbSession, user: AdminUser):
    if await session.scalar(
        select(DeliveryMan).where(
            or_(DeliveryMan.email == payload.email, DeliveryMan.mobile == payload.mobile)
        )
    ):
        raise HTTPException(409, "Delivery partner already exists")
    data = payload.model_dump()
    password = data.pop("password") or "ChangeMe123!"
    man = DeliveryMan(**data, password_hash=hash_password(password))
    session.add(man)
    await session.flush()
    await log(session, man.id, "created", "Delivery partner added")
    await session.commit()
    await session.refresh(man)
    return await serialize(session, man)


@router.get("/detail/{man_id}", response_model=DeliveryRead)
async def get(man_id: UUID, session: DbSession, user: AdminUser):
    man = await session.get(DeliveryMan, man_id)
    if not man:
        raise HTTPException(404, "Delivery partner not found")
    return await serialize(session, man)


@router.patch("/detail/{man_id}", response_model=DeliveryRead)
async def patch(man_id: UUID, payload: DeliveryPatch, session: DbSession, user: AdminUser):
    man = await session.get(DeliveryMan, man_id)
    if not man:
        raise HTTPException(404, "Delivery partner not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(man, k, v)
    if payload.online is not None or payload.latitude is not None:
        man.last_active_at = datetime.now(timezone.utc)
    await log(session, man.id, "status_changed", str(payload.model_dump(exclude_unset=True)))
    await session.commit()
    await session.refresh(man)
    return await serialize(session, man)


@router.delete("/detail/{man_id}", status_code=204)
async def delete(man_id: UUID, session: DbSession, user: AdminUser):
    man = await session.get(DeliveryMan, man_id)
    if not man:
        raise HTTPException(404, "Delivery partner not found")
    await session.delete(man)
    await session.commit()
    return Response(status_code=204)


@router.post("/assign/order")
async def assign(payload: AssignInput, session: DbSession, user: AdminUser):
    man = await session.get(DeliveryMan, payload.delivery_man_id)
    order = await session.get(Order, payload.order_id)
    if not man or not order:
        raise HTTPException(404, "Order or delivery partner not found")
    if order.status in {"delivered", "cancelled", "failed"}:
        raise HTTPException(409, "Completed or cancelled orders cannot be assigned")
    if not man.active or man.blocked or man.verification_status != "verified":
        raise HTTPException(409, "Select an active, verified delivery partner")
    active_order = await session.scalar(
        select(Order.id)
        .where(
            Order.delivery_man_id == man.id,
            Order.id != order.id,
            Order.status.notin_(["delivered", "cancelled", "failed"]),
        )
        .limit(1)
    )
    if active_order:
        raise HTTPException(409, "This delivery partner already has an active order")
    previous_id = order.delivery_man_id
    if previous_id and previous_id != man.id:
        previous = await session.get(DeliveryMan, previous_id)
        if previous:
            previous.delivery_status = "available" if previous.online else "offline"
            await log(session, previous.id, "order_reassigned", str(order.id))
            await delivery_sockets.to_delivery(
                previous.id, "order_reassigned", {"order_id": str(order.id)}
            )
    order.delivery_man_id = man.id
    order.status = "assigned"
    order.delivery_otp = order.delivery_otp or f"{secrets.randbelow(1000000):06d}"
    man.delivery_status = "assigned"
    await log(session, man.id, "order_assigned", str(order.id))
    await session.commit()
    tokens = list(
        await session.scalars(
            select(PushDevice.token).where(
                PushDevice.delivery_man_id == man.id, PushDevice.active.is_(True)
            )
        )
    )
    await send_push(
        tokens,
        "New delivery assigned",
        f"Order #{str(order.id)[:8].upper()} is ready for you",
        {"type": "order_assigned", "order_id": str(order.id), "route": "orders"},
    )
    customer_tokens = list(
        await session.scalars(
            select(PushDevice.token).where(
                PushDevice.user_id == order.user_id,
                PushDevice.app_kind == "customer",
                PushDevice.active.is_(True),
            )
        )
    )
    await send_push(
        customer_tokens,
        "Delivery partner assigned",
        f"A delivery partner has been assigned to order #{str(order.id)[:8].upper()}",
        {
            "type": "order_status",
            "order_id": str(order.id),
            "status": "assigned",
            "route": "orders",
        },
    )
    await delivery_sockets.to_delivery(man.id, "order_assigned", {"order_id": str(order.id)})
    await delivery_sockets.to_customer(
        order.user_id, "order_status_updated", {"order_id": str(order.id), "status": "assigned"}
    )
    await delivery_sockets.to_admins(
        "delivery_updated", {"delivery_man_id": str(man.id), "order_id": str(order.id)}
    )
    return {"ok": True}


@router.get("/operations/attendance")
async def attendance(session: DbSession, user: AdminUser):
    return list(
        await session.scalars(
            select(DeliveryAttendance).order_by(DeliveryAttendance.created_at.desc())
        )
    )


@router.get("/operations/earnings")
async def earnings(session: DbSession, user: AdminUser):
    return list(
        await session.scalars(select(DeliveryEarning).order_by(DeliveryEarning.created_at.desc()))
    )


@router.get("/operations/leaves")
async def leaves(session: DbSession, user: AdminUser):
    return list(
        await session.scalars(select(DeliveryLeave).order_by(DeliveryLeave.created_at.desc()))
    )


@router.patch("/operations/leaves/{leave_id}")
async def decide_leave(leave_id: UUID, payload: LeaveDecision, session: DbSession, user: AdminUser):
    leave = await session.get(DeliveryLeave, leave_id)
    if not leave:
        raise HTTPException(404, "Leave request not found")
    leave.status = payload.status
    leave.admin_note = payload.admin_note
    await log(session, leave.delivery_man_id, "leave_decided", payload.status)
    await session.commit()
    return leave


@router.post("/operations/notifications", status_code=201)
async def notify(payload: NotificationInput, session: DbSession, user: AdminUser):
    note = DeliveryNotification(**payload.model_dump())
    session.add(note)
    await session.commit()
    query = select(PushDevice.token).where(
        PushDevice.app_kind == "delivery", PushDevice.active.is_(True)
    )
    if payload.delivery_man_id:
        query = query.where(PushDevice.delivery_man_id == payload.delivery_man_id)
    tokens = list(await session.scalars(query))
    await send_push(
        tokens, payload.title, payload.message, {"type": payload.kind, "route": "notifications"}
    )
    event = {
        "notification_id": str(note.id),
        "kind": payload.kind,
        "title": payload.title,
        "message": payload.message,
    }
    if payload.delivery_man_id:
        await delivery_sockets.to_delivery(payload.delivery_man_id, "notification", event)
    else:
        await delivery_sockets.to_all_delivery("notification", event)
    await delivery_sockets.to_admins("notification_sent", event)
    return note


@router.get("/operations/logs")
async def logs(session: DbSession, user: AdminUser):
    return list(
        await session.scalars(
            select(DeliveryActivity).order_by(DeliveryActivity.created_at.desc()).limit(500)
        )
    )


@router.post("/{man_id}/reset-password", status_code=204)
async def reset_password(
    man_id: UUID, payload: ResetPasswordInput, session: DbSession, user: AdminUser
):
    man = await session.get(DeliveryMan, man_id)
    if not man:
        raise HTTPException(404, "Delivery partner not found")
    man.password_hash = hash_password(payload.password)
    await log(session, man.id, "password_reset")
    await session.commit()
    return Response(status_code=204)
