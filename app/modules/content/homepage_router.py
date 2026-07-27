from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.exceptions import AppError
from app.integrations.storage.r2 import R2Storage
from app.modules.catalog.category_model import Category
from app.modules.catalog.management_models import Product
from app.modules.content.homepage_model import (
    ClientFeedback,
    HeroSlide,
    HomepageBanner,
    HomepageFreshPick,
    HomepageTopCategory,
    HomepageTrendingProduct,
    HomepageWeeklyDeal,
)
from app.modules.content.homepage_schemas import (
    ClientFeedbackCreate,
    ClientFeedbackRead,
    FreshPicksUpdate,
    HeroSlideCreate,
    HeroSlideRead,
    HomepageBannerRead,
    HomepageBannerUpdate,
    StorefrontHomepageRead,
    TopCategoriesUpdate,
)

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]


async def find_slide(session: AsyncSession, slide_id: UUID) -> HeroSlide:
    slide = await session.get(HeroSlide, slide_id)
    if not slide:
        raise AppError("Hero slide not found", 404)
    return slide


@router.get("/storefront", response_model=StorefrontHomepageRead)
async def get_storefront_homepage(session: DbSession):
    """Return all public homepage configuration in one network request."""
    hero_slides = list(
        await session.scalars(
            select(HeroSlide)
            .where(HeroSlide.active.is_(True))
            .order_by(HeroSlide.sort_order, HeroSlide.created_at.desc())
        )
    )
    top_category_ids = list(
        await session.scalars(
            select(HomepageTopCategory.category_id).order_by(HomepageTopCategory.sort_order)
        )
    )
    fresh_pick_ids = list(
        await session.scalars(
            select(HomepageFreshPick.product_id).order_by(HomepageFreshPick.sort_order)
        )
    )
    trending_product_ids = list(
        await session.scalars(
            select(HomepageTrendingProduct.product_id).order_by(HomepageTrendingProduct.sort_order)
        )
    )
    banners = list(
        await session.scalars(
            select(HomepageBanner).where(
                HomepageBanner.section_key.in_(("section-one", "section-two"))
            )
        )
    )
    banner_by_key = {banner.section_key: banner for banner in banners}
    weekly_deal_ids = list(
        await session.scalars(
            select(HomepageWeeklyDeal.product_id).order_by(HomepageWeeklyDeal.sort_order)
        )
    )
    client_feedback = list(
        await session.scalars(
            select(ClientFeedback)
            .where(ClientFeedback.active.is_(True))
            .order_by(ClientFeedback.sort_order, ClientFeedback.created_at.desc())
        )
    )
    product_ids = set(fresh_pick_ids + trending_product_ids + weekly_deal_ids)
    products = (
        list(
            await session.scalars(
                select(Product).where(
                    Product.id.in_(product_ids),
                    Product.is_active.is_(True),
                    Product.archived.is_(False),
                )
            )
        )
        if product_ids
        else []
    )
    return {
        "hero_slides": hero_slides,
        "top_category_ids": top_category_ids,
        "fresh_pick_ids": fresh_pick_ids,
        "trending_product_ids": trending_product_ids,
        "banner_one": banner_by_key.get("section-one"),
        "weekly_deal_ids": weekly_deal_ids,
        "banner_two": banner_by_key.get("section-two"),
        "client_feedback": client_feedback,
        "products": products,
    }


@router.get("/hero-slides", response_model=list[HeroSlideRead])
async def list_hero_slides(session: DbSession, active_only: bool = False):
    query = select(HeroSlide)
    if active_only:
        query = query.where(HeroSlide.active.is_(True))
    result = await session.scalars(
        query.order_by(HeroSlide.sort_order, HeroSlide.created_at.desc())
    )
    return list(result)


@router.post("/hero-slides", response_model=HeroSlideRead, status_code=status.HTTP_201_CREATED)
async def create_hero_slide(payload: HeroSlideCreate, session: DbSession):
    slide = HeroSlide(**payload.model_dump())
    session.add(slide)
    await session.commit()
    await session.refresh(slide)
    return slide


@router.put("/hero-slides/{slide_id}", response_model=HeroSlideRead)
async def update_hero_slide(slide_id: UUID, payload: HeroSlideCreate, session: DbSession):
    slide = await find_slide(session, slide_id)
    for field, value in payload.model_dump().items():
        setattr(slide, field, value)
    await session.commit()
    await session.refresh(slide)
    return slide


@router.patch("/hero-slides/{slide_id}/toggle", response_model=HeroSlideRead)
async def toggle_hero_slide(slide_id: UUID, session: DbSession):
    slide = await find_slide(session, slide_id)
    slide.active = not slide.active
    await session.commit()
    await session.refresh(slide)
    return slide


@router.post("/hero-slides/{slide_id}/image", response_model=HeroSlideRead)
async def upload_hero_image(slide_id: UUID, session: DbSession, image: UploadFile = File(...)):
    slide = await find_slide(session, slide_id)
    storage = R2Storage()
    content, extension = await storage.read_image(image)
    filename = storage.safe_filename(f"hero-{slide.id}", extension)
    key = f"homepage/hero/{slide.id}/{filename}"
    await storage.put(key, content, image.content_type or "image/webp")
    slide.image_url = storage.public_url(key)
    await session.commit()
    await session.refresh(slide)
    return slide


@router.delete("/hero-slides/{slide_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hero_slide(slide_id: UUID, session: DbSession):
    slide = await find_slide(session, slide_id)
    await session.delete(slide)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/top-categories", response_model=list[UUID])
async def list_top_categories(session: DbSession):
    result = await session.scalars(
        select(HomepageTopCategory.category_id).order_by(HomepageTopCategory.sort_order)
    )
    return list(result)


@router.put("/top-categories", response_model=list[UUID])
async def update_top_categories(payload: TopCategoriesUpdate, session: DbSession):
    category_ids = list(dict.fromkeys(payload.category_ids))
    if category_ids:
        existing = set(
            await session.scalars(select(Category.id).where(Category.id.in_(category_ids)))
        )
        missing = [category_id for category_id in category_ids if category_id not in existing]
        if missing:
            raise AppError("One or more selected categories no longer exist", 422)
    await session.execute(delete(HomepageTopCategory))
    session.add_all(
        HomepageTopCategory(category_id=category_id, sort_order=index)
        for index, category_id in enumerate(category_ids)
    )
    await session.commit()
    return category_ids


@router.get("/fresh-picks", response_model=list[UUID])
async def list_fresh_picks(session: DbSession):
    result = await session.scalars(
        select(HomepageFreshPick.product_id).order_by(HomepageFreshPick.sort_order)
    )
    return list(result)


@router.put("/fresh-picks", response_model=list[UUID])
async def update_fresh_picks(payload: FreshPicksUpdate, session: DbSession):
    product_ids = list(dict.fromkeys(payload.product_ids))
    if product_ids:
        existing = set(await session.scalars(select(Product.id).where(Product.id.in_(product_ids))))
        if any(product_id not in existing for product_id in product_ids):
            raise AppError("One or more selected products no longer exist", 422)
    await session.execute(delete(HomepageFreshPick))
    session.add_all(
        HomepageFreshPick(product_id=product_id, sort_order=index)
        for index, product_id in enumerate(product_ids)
    )
    await session.commit()
    return product_ids


@router.get("/trending-products", response_model=list[UUID])
async def list_trending_products(session: DbSession):
    result = await session.scalars(
        select(HomepageTrendingProduct.product_id).order_by(HomepageTrendingProduct.sort_order)
    )
    return list(result)


@router.put("/trending-products", response_model=list[UUID])
async def update_trending_products(payload: FreshPicksUpdate, session: DbSession):
    product_ids = list(dict.fromkeys(payload.product_ids))
    if product_ids:
        existing = set(await session.scalars(select(Product.id).where(Product.id.in_(product_ids))))
        if any(product_id not in existing for product_id in product_ids):
            raise AppError("One or more selected products no longer exist", 422)
    await session.execute(delete(HomepageTrendingProduct))
    session.add_all(
        HomepageTrendingProduct(product_id=product_id, sort_order=index)
        for index, product_id in enumerate(product_ids)
    )
    await session.commit()
    return product_ids


@router.get("/banners/{section_key}", response_model=HomepageBannerRead | None)
async def get_banner(section_key: str, session: DbSession):
    return await session.scalar(
        select(HomepageBanner).where(HomepageBanner.section_key == section_key)
    )


@router.put("/banners/{section_key}", response_model=HomepageBannerRead)
async def update_banner(section_key: str, payload: HomepageBannerUpdate, session: DbSession):
    banner = await session.scalar(
        select(HomepageBanner).where(HomepageBanner.section_key == section_key)
    )
    if not banner:
        banner = HomepageBanner(section_key=section_key)
        session.add(banner)
    for field, value in payload.model_dump().items():
        setattr(banner, field, value)
    await session.commit()
    await session.refresh(banner)
    return banner


@router.post("/banners/{section_key}/image", response_model=HomepageBannerRead)
async def upload_banner_image(section_key: str, session: DbSession, image: UploadFile = File(...)):
    banner = await session.scalar(
        select(HomepageBanner).where(HomepageBanner.section_key == section_key)
    )
    if not banner:
        banner = HomepageBanner(section_key=section_key)
        session.add(banner)
        await session.flush()
    storage = R2Storage()
    content, extension = await storage.read_image(image)
    filename = storage.safe_filename(
        f"banner-{section_key}-{banner.id}-{uuid4().hex[:12]}", extension
    )
    key = f"homepage/banners/{section_key}/{filename}"
    await storage.put(key, content, image.content_type or "image/webp")
    banner.image_url = storage.public_url(key)
    await session.commit()
    await session.refresh(banner)
    return banner


@router.get("/weekly-deals", response_model=list[UUID])
async def list_weekly_deals(session: DbSession):
    result = await session.scalars(
        select(HomepageWeeklyDeal.product_id).order_by(HomepageWeeklyDeal.sort_order)
    )
    return list(result)


@router.put("/weekly-deals", response_model=list[UUID])
async def update_weekly_deals(payload: FreshPicksUpdate, session: DbSession):
    product_ids = list(dict.fromkeys(payload.product_ids))
    if product_ids:
        existing = set(await session.scalars(select(Product.id).where(Product.id.in_(product_ids))))
        if any(product_id not in existing for product_id in product_ids):
            raise AppError("One or more selected products no longer exist", 422)
    await session.execute(delete(HomepageWeeklyDeal))
    session.add_all(
        HomepageWeeklyDeal(product_id=product_id, sort_order=index)
        for index, product_id in enumerate(product_ids)
    )
    await session.commit()
    return product_ids


@router.get("/client-feedback", response_model=list[ClientFeedbackRead])
async def list_client_feedback(session: DbSession, active_only: bool = False):
    query = select(ClientFeedback)
    if active_only:
        query = query.where(ClientFeedback.active.is_(True))
    result = await session.scalars(
        query.order_by(ClientFeedback.sort_order, ClientFeedback.created_at.desc())
    )
    return list(result)


@router.post(
    "/client-feedback", response_model=ClientFeedbackRead, status_code=status.HTTP_201_CREATED
)
async def create_client_feedback(payload: ClientFeedbackCreate, session: DbSession):
    item = ClientFeedback(**payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


@router.put("/client-feedback/{feedback_id}", response_model=ClientFeedbackRead)
async def update_client_feedback(
    feedback_id: UUID, payload: ClientFeedbackCreate, session: DbSession
):
    item = await session.get(ClientFeedback, feedback_id)
    if not item:
        raise AppError("Client feedback not found", 404)
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    await session.commit()
    await session.refresh(item)
    return item


@router.post("/client-feedback/{feedback_id}/avatar", response_model=ClientFeedbackRead)
async def upload_feedback_avatar(
    feedback_id: UUID, session: DbSession, image: UploadFile = File(...)
):
    item = await session.get(ClientFeedback, feedback_id)
    if not item:
        raise AppError("Client feedback not found", 404)
    storage = R2Storage()
    content, extension = await storage.read_image(image)
    filename = storage.safe_filename(f"client-{item.id}-{uuid4().hex[:12]}", extension)
    key = f"homepage/client-feedback/{item.id}/{filename}"
    await storage.put(key, content, image.content_type or "image/webp")
    item.avatar_url = storage.public_url(key)
    await session.commit()
    await session.refresh(item)
    return item


@router.delete("/client-feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client_feedback(feedback_id: UUID, session: DbSession):
    item = await session.get(ClientFeedback, feedback_id)
    if not item:
        raise AppError("Client feedback not found", 404)
    await session.delete(item)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
