from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from app.modules.auth.dependencies import admin_user
from app.modules.auth.model import User
from app.modules.catalog.management_models import Product
from app.modules.customers.address_router import DbSession
from app.modules.delivery.models import DeliveryEarning, DeliveryMan
from app.modules.orders.models import Order, OrderItem

router = APIRouter()
AdminUser = Annotated[User, Depends(admin_user)]
FINAL_STATUSES = ("delivered", "cancelled", "failed")
EXCLUDED_REVENUE_STATUSES = ("cancelled", "failed")


@router.get("")
async def admin_dashboard(session: DbSession, _: AdminUser):
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today - timedelta(days=6)

    order_summary = (
        await session.execute(
            select(
                func.count(Order.id),
                func.coalesce(
                    func.sum(Order.total).filter(Order.status.notin_(EXCLUDED_REVENUE_STATUSES)),
                    0,
                ),
                func.count(Order.id).filter(Order.created_at >= today),
                func.coalesce(
                    func.sum(Order.total).filter(
                        Order.created_at >= today,
                        Order.status.notin_(EXCLUDED_REVENUE_STATUSES),
                    ),
                    0,
                ),
                func.count(Order.id).filter(Order.status.notin_(FINAL_STATUSES)),
            )
        )
    ).one()
    customer_summary = (
        await session.execute(
            select(
                func.count(User.id),
                func.count(User.id).filter(User.active.is_(True)),
            ).where(User.role == "customer")
        )
    ).one()
    product_summary = (
        await session.execute(
            select(
                func.count(Product.id),
                func.count(Product.id).filter(
                    Product.is_active.is_(True), Product.inventory_qty <= 10
                ),
            ).where(Product.archived.is_(False))
        )
    ).one()

    status_rows = (
        await session.execute(select(Order.status, func.count(Order.id)).group_by(Order.status))
    ).all()
    weekly_orders = (
        await session.execute(
            select(Order.created_at, Order.total).where(
                Order.created_at >= week_start,
                Order.status.notin_(EXCLUDED_REVENUE_STATUSES),
            )
        )
    ).all()
    recent_rows = (
        await session.execute(
            select(Order.id, Order.created_at, Order.status, Order.total, User.name)
            .outerjoin(User, User.id == Order.user_id)
            .order_by(Order.created_at.desc())
            .limit(6)
        )
    ).all()
    top_rows = (
        await session.execute(
            select(
                OrderItem.product_id,
                OrderItem.product_name,
                func.sum(OrderItem.quantity).label("quantity"),
                func.sum(OrderItem.line_total).label("revenue"),
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(Order.status.notin_(EXCLUDED_REVENUE_STATUSES))
            .group_by(OrderItem.product_id, OrderItem.product_name)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(5)
        )
    ).all()
    low_stock_rows = list(
        await session.scalars(
            select(Product)
            .where(
                Product.archived.is_(False),
                Product.is_active.is_(True),
                Product.inventory_qty <= 10,
            )
            .order_by(Product.inventory_qty, Product.name)
            .limit(6)
        )
    )

    delivery_summary = (
        await session.execute(
            select(
                func.count(DeliveryMan.id),
                func.count(DeliveryMan.id).filter(DeliveryMan.active.is_(True)),
            )
        )
    ).one()
    today_deliveries = await session.scalar(
        select(func.count(Order.id)).where(
            Order.updated_at >= today, Order.status == "delivered"
        )
    )
    today_earnings = await session.scalar(
        select(func.coalesce(func.sum(DeliveryEarning.amount), 0)).where(
            DeliveryEarning.created_at >= today
        )
    )

    sales_by_day = {
        (week_start + timedelta(days=offset)).date(): {"revenue": 0, "orders": 0}
        for offset in range(7)
    }
    for created_at, total in weekly_orders:
        day = created_at.date()
        if day in sales_by_day:
            sales_by_day[day]["revenue"] += total
            sales_by_day[day]["orders"] += 1

    return {
        "summary": {
            "revenue": order_summary[1],
            "today_revenue": order_summary[3],
            "total_orders": order_summary[0],
            "today_orders": order_summary[2],
            "active_orders": order_summary[4],
            "customers": customer_summary[0],
            "active_customers": customer_summary[1],
            "products": product_summary[0],
            "low_stock": product_summary[1],
        },
        "order_statuses": dict(status_rows),
        "sales_days": [
            {
                "date": day.isoformat(),
                "label": day.strftime("%a"),
                **values,
            }
            for day, values in sales_by_day.items()
        ],
        "recent_orders": [
            {
                "id": row.id,
                "created_at": row.created_at,
                "status": row.status,
                "total": row.total,
                "customer_name": row.name,
            }
            for row in recent_rows
        ],
        "top_products": [
            {
                "product_id": row.product_id,
                "name": row.product_name,
                "quantity": row.quantity,
                "revenue": row.revenue,
            }
            for row in top_rows
        ],
        "low_stock_products": [
            {
                "id": product.id,
                "name": product.name,
                "category_l1": product.category_l1,
                "inventory_qty": product.inventory_qty,
                "unit": product.unit,
            }
            for product in low_stock_rows
        ],
        "delivery": {
            "total": delivery_summary[0],
            "active": delivery_summary[1],
            "today_deliveries": today_deliveries or 0,
            "today_earnings": today_earnings,
        },
    }
