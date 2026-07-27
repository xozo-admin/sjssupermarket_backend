from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.modules.catalog.management_models import Product
from app.modules.catalog.management_schemas import ProductRead
from app.modules.customers.address_router import CurrentUser, DbSession
from app.modules.customers.wishlist_model import WishlistItem

router = APIRouter()


@router.get("", response_model=list[ProductRead])
async def list_wishlist(session: DbSession, user: CurrentUser):
    return list(
        await session.scalars(
            select(Product)
            .join(WishlistItem, WishlistItem.product_id == Product.id)
            .where(WishlistItem.user_id == user.id, Product.is_active.is_(True))
            .order_by(WishlistItem.created_at.desc())
        )
    )


@router.post("/{product_id}", status_code=status.HTTP_201_CREATED)
async def add_wishlist(product_id: UUID, session: DbSession, user: CurrentUser):
    product = await session.get(Product, product_id)
    if not product or not product.is_active:
        raise HTTPException(status_code=404, detail="Product not found")
    existing = await session.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == user.id,
            WishlistItem.product_id == product_id,
        )
    )
    if not existing:
        session.add(WishlistItem(user_id=user.id, product_id=product_id))
        await session.commit()
    return {"ok": True}


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_wishlist(product_id: UUID, session: DbSession, user: CurrentUser):
    item = await session.scalar(
        select(WishlistItem).where(
            WishlistItem.user_id == user.id,
            WishlistItem.product_id == product_id,
        )
    )
    if item:
        await session.delete(item)
        await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
