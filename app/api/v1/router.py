from fastapi import APIRouter

from app.api.v1.public.router import router as public_router
from app.modules.catalog.router import router as catalog_router
from app.modules.catalog.category_router import router as category_router
from app.modules.catalog.management_router import router as management_router
from app.modules.orders.router import router as orders_router
from app.modules.refunds.router import router as refunds_router
from app.modules.content.homepage_router import router as homepage_router
from app.modules.auth.router import router as auth_router
from app.modules.customers.address_router import router as customer_router
from app.modules.customers.admin_router import router as customer_admin_router
from app.modules.customers.wishlist_router import router as wishlist_router
from app.modules.delivery.router import router as delivery_router
from app.modules.delivery.mobile_router import router as delivery_mobile_router
from app.modules.notifications.router import router as notifications_router
from app.modules.payments.router import router as payments_router
from app.modules.pos.router import router as pos_router
from app.modules.staff.router import router as staff_router
from app.modules.suppliers.router import router as suppliers_router
from app.modules.shipping.router import (
    public_router as shipping_public_router,
    router as shipping_router,
)
from app.modules.dashboard.router import router as dashboard_router
from app.realtime.delivery import router as delivery_socket_router

router = APIRouter()
router.include_router(auth_router, prefix="/auth", tags=["authentication"])
router.include_router(customer_router, prefix="/customers", tags=["customers"])
router.include_router(customer_admin_router, prefix="/admin/customers", tags=["admin customers"])
router.include_router(wishlist_router, prefix="/wishlist", tags=["wishlist"])
router.include_router(delivery_router, prefix="/admin/delivery-men", tags=["delivery management"])
router.include_router(delivery_mobile_router, prefix="/delivery", tags=["delivery partner"])
router.include_router(notifications_router, prefix="/notifications", tags=["notifications"])
router.include_router(payments_router, prefix="/payments", tags=["payments"])
router.include_router(pos_router, prefix="/admin/pos", tags=["point of sale"])
router.include_router(staff_router, prefix="/admin/staff", tags=["staff access"])
router.include_router(suppliers_router, prefix="/admin/suppliers", tags=["supplier procurement"])
router.include_router(
    shipping_router, prefix="/admin/shipping-zone", tags=["shipping configuration"]
)
router.include_router(shipping_public_router, prefix="/shipping", tags=["shipping"])
router.include_router(dashboard_router, prefix="/admin/dashboard", tags=["admin dashboard"])
router.include_router(delivery_socket_router, prefix="/ws", tags=["realtime"])
router.include_router(public_router)
router.include_router(catalog_router, prefix="/products", tags=["products"])
router.include_router(category_router, prefix="/categories", tags=["categories"])
router.include_router(management_router, prefix="/catalog", tags=["catalog management"])
router.include_router(orders_router, prefix="/orders", tags=["orders"])
router.include_router(refunds_router, prefix="/refunds", tags=["refunds"])
router.include_router(homepage_router, prefix="/homepage", tags=["homepage appearance"])
