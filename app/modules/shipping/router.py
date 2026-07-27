from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.modules.auth.dependencies import admin_user
from app.modules.auth.model import User
from app.modules.customers.address_router import DbSession
from app.modules.shipping.models import ShippingZoneConfiguration
from app.modules.shipping.schemas import DeliveryAvailability, ShippingZoneInput, ShippingZoneRead
from app.modules.shipping.service import delivery_availability

router = APIRouter()
public_router = APIRouter()
AdminUser = Annotated[User, Depends(admin_user)]


async def get_or_create(session: DbSession) -> ShippingZoneConfiguration:
    config = await session.scalar(select(ShippingZoneConfiguration).limit(1))
    if config is None:
        config = ShippingZoneConfiguration(
            store_name="SJS Super Market",
            store_address="",
            latitude=13.0827,
            longitude=80.2707,
            radius_km=5,
            delivery_fee=0,
            enabled=True,
        )
        session.add(config)
        await session.commit()
        await session.refresh(config)
    return config


@router.get("", response_model=ShippingZoneRead)
async def read_shipping_zone(session: DbSession, user: AdminUser):
    return await get_or_create(session)


@router.put("", response_model=ShippingZoneRead)
async def update_shipping_zone(payload: ShippingZoneInput, session: DbSession, user: AdminUser):
    config = await get_or_create(session)
    for field, value in payload.model_dump().items():
        setattr(config, field, value)
    await session.commit()
    await session.refresh(config)
    return config


@public_router.get("/availability", response_model=DeliveryAvailability)
async def check_delivery_availability(latitude: float, longitude: float, session: DbSession):
    available, distance, zone = await delivery_availability(session, latitude, longitude)
    radius = zone.radius_km if zone else None
    if available:
        message = (
            f"Delivery is available for this location ({distance:.1f} km from the supermarket)."
        )
    elif zone is None or not zone.enabled:
        message = "Delivery is currently unavailable."
    else:
        message = f"Delivery is not available for your location. It is {distance:.1f} km away; our delivery range is {zone.radius_km:g} km."
    return DeliveryAvailability(
        available=available, distance_km=round(distance, 2), radius_km=radius, message=message
    )
