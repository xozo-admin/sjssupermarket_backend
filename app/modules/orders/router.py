from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select

from app.modules.catalog.management_models import Product
from app.modules.customers.address_model import CustomerAddress
from app.modules.orders.models import Order, OrderItem
from app.modules.orders.schemas import OrderCreate, OrderRead, OrderStatusUpdate, OrderSummary
from app.modules.customers.address_router import CurrentUser, DbSession
from app.modules.auth.dependencies import admin_user
from app.modules.auth.model import User
from app.modules.delivery.models import DeliveryMan
from fastapi import Depends
from typing import Annotated
from app.realtime.delivery import delivery_sockets
from app.modules.shipping.service import require_deliverable_address
from app.modules.notifications.firebase import send_push
from app.modules.notifications.models import PushDevice

router = APIRouter()
AdminUser = Annotated[User, Depends(admin_user)]


async def serialize_orders(session, orders: list[Order]) -> list[dict]:
    order_ids = [order.id for order in orders]
    user_ids = list({order.user_id for order in orders})
    items = (
        list(
            await session.scalars(
                select(OrderItem)
                .where(OrderItem.order_id.in_(order_ids))
                .order_by(OrderItem.created_at)
            )
        )
        if order_ids
        else []
    )
    users = (
        list(await session.scalars(select(User).where(User.id.in_(user_ids)))) if user_ids else []
    )
    users_by_id = {account.id: account for account in users}
    man_ids = list({order.delivery_man_id for order in orders if order.delivery_man_id})
    men = (
        list(await session.scalars(select(DeliveryMan).where(DeliveryMan.id.in_(man_ids))))
        if man_ids
        else []
    )
    men_by_id = {man.id: man for man in men}
    grouped: dict = {order_id: [] for order_id in order_ids}
    for item in items:
        grouped[item.order_id].append(item)
    return [
        OrderRead.model_validate(
            {
                **order.__dict__,
                "customer_name": users_by_id.get(order.user_id).name
                if users_by_id.get(order.user_id)
                else None,
                "customer_email": users_by_id.get(order.user_id).email
                if users_by_id.get(order.user_id)
                else None,
                "customer_mobile": users_by_id.get(order.user_id).mobile
                if users_by_id.get(order.user_id)
                else None,
                "delivery_man_name": men_by_id.get(order.delivery_man_id).name
                if men_by_id.get(order.delivery_man_id)
                else None,
                "delivery_latitude": men_by_id.get(order.delivery_man_id).latitude
                if men_by_id.get(order.delivery_man_id)
                else None,
                "delivery_longitude": men_by_id.get(order.delivery_man_id).longitude
                if men_by_id.get(order.delivery_man_id)
                else None,
                "items": grouped[order.id],
            }
        ).model_dump()
        for order in orders
    ]


@router.get("", response_model=list[OrderRead])
async def list_my_orders(session: DbSession, user: CurrentUser):
    orders = list(
        await session.scalars(
            select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
        )
    )
    return await serialize_orders(session, orders)


@router.get("/admin", response_model=list[OrderRead])
async def list_all_orders(session: DbSession, user: AdminUser):
    orders = list(await session.scalars(select(Order).order_by(Order.created_at.desc())))
    return await serialize_orders(session, orders)


@router.patch("/admin/{order_id}/status", response_model=OrderRead)
async def update_order_status(
    order_id: UUID, payload: OrderStatusUpdate, session: DbSession, user: AdminUser
):
    order = await session.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = payload.status
    await session.commit()
    await session.refresh(order)
    serialized = (await serialize_orders(session, [order]))[0]
    event_data = jsonable_encoder(serialized)
    await delivery_sockets.to_admins("order_status_updated", event_data)
    await delivery_sockets.to_customer(
        order.user_id, "order_status_updated", {"order_id": str(order.id), "status": order.status}
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
    title = {
        "placed": "Order placed",
        "assigned": "Delivery partner assigned",
        "accepted": "Order accepted",
        "picked_up": "Order picked up",
        "on_the_way": "Order is on the way",
        "delivered": "Order delivered",
        "cancelled": "Order cancelled",
        "failed": "Delivery failed",
    }.get(order.status, "Order updated")
    await send_push(
        customer_tokens,
        title,
        f"Order #{str(order.id)[:8].upper()} is now {order.status.replace('_', ' ')}",
        {
            "type": "order_status",
            "order_id": str(order.id),
            "status": order.status,
            "route": "orders",
        },
    )
    if order.delivery_man_id:
        await delivery_sockets.to_delivery(
            order.delivery_man_id,
            "order_status_updated",
            {"order_id": str(order.id), "status": order.status},
        )
    return serialized


@router.post("", response_model=OrderSummary, status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate, session: DbSession, user: CurrentUser):
    if payload.payment_method != "cod":
        raise HTTPException(
            status_code=400,
            detail="Use the Razorpay checkout endpoint for online payments",
        )
    return await create_customer_order(payload, session, user)


async def create_customer_order(
    payload: OrderCreate,
    session: DbSession,
    user: CurrentUser,
    *,
    payment_status: str = "pending",
):
    address = await session.scalar(
        select(CustomerAddress).where(
            CustomerAddress.id == payload.address_id, CustomerAddress.user_id == user.id
        )
    )
    if not address:
        raise HTTPException(status_code=404, detail="Delivery address not found")
    await require_deliverable_address(session, address)

    quantities: dict = {}
    for item in payload.items:
        quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
    products = list(
        await session.scalars(select(Product).where(Product.id.in_(quantities)).with_for_update())
    )
    if len(products) != len(quantities):
        raise HTTPException(status_code=400, detail="One or more products are no longer available")
    for product in products:
        if (
            not product.is_active
            or product.stock_status != "in_stock"
            or product.inventory_qty < quantities[product.id]
        ):
            raise HTTPException(status_code=409, detail=f"Insufficient stock for {product.name}")

    subtotal = sum(
        (product.selling_price * quantities[product.id] for product in products), Decimal("0")
    )
    # delivery_fee = Decimal("40") if subtotal < Decimal("500") else Decimal("0")
    delivery_fee = Decimal("0")
    address_text = ", ".join(
        filter(
            None,
            [
                address.full_name,
                address.mobile,
                address.street,
                address.locality,
                address.city,
                address.state,
                address.pincode,
                address.landmark,
            ],
        )
    )
    order = Order(
        user_id=user.id,
        address_id=address.id,
        status="placed",
        payment_method=payload.payment_method,
        payment_status=payment_status,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total=subtotal + delivery_fee,
        delivery_address=address_text,
    )
    session.add(order)
    await session.flush()
    for product in products:
        quantity = quantities[product.id]
        product.inventory_qty -= quantity
        if product.inventory_qty == 0:
            product.stock_status = "out_of_stock"
        session.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                product_name=product.name,
                unit_price=product.selling_price,
                quantity=quantity,
                line_total=product.selling_price * quantity,
            )
        )
    await session.commit()
    await session.refresh(order)
    serialized = (await serialize_orders(session, [order]))[0]
    await delivery_sockets.to_admins("order_created", jsonable_encoder(serialized))
    return order
