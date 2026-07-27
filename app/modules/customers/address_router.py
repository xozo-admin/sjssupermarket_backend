from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select, update

from app.modules.auth.dependencies import current_user
from app.modules.auth.model import User
from app.modules.customers.address_model import CustomerAddress
from app.modules.customers.address_schemas import AddressInput, AddressRead
from app.database.session import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from app.modules.orders.models import Order

router = APIRouter()
DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(current_user)]


async def owned_address(session: AsyncSession, user_id: UUID, address_id: UUID) -> CustomerAddress:
    address = await session.scalar(
        select(CustomerAddress).where(
            CustomerAddress.id == address_id, CustomerAddress.user_id == user_id
        )
    )
    if not address:
        raise HTTPException(status_code=404, detail="Delivery address not found")
    return address


@router.get("/addresses", response_model=list[AddressRead])
async def list_addresses(session: DbSession, user: CurrentUser):
    result = await session.scalars(
        select(CustomerAddress)
        .where(CustomerAddress.user_id == user.id)
        .order_by(CustomerAddress.is_default.desc(), CustomerAddress.updated_at.desc())
    )
    return list(result)


@router.post("/addresses", response_model=AddressRead, status_code=status.HTTP_201_CREATED)
async def create_address(payload: AddressInput, session: DbSession, user: CurrentUser):
    if payload.is_default:
        await session.execute(
            update(CustomerAddress)
            .where(CustomerAddress.user_id == user.id)
            .values(is_default=False)
        )
    address = CustomerAddress(user_id=user.id, **payload.model_dump())
    session.add(address)
    await session.commit()
    await session.refresh(address)
    return address


@router.put("/addresses/{address_id}", response_model=AddressRead)
async def update_address(
    address_id: UUID, payload: AddressInput, session: DbSession, user: CurrentUser
):
    address = await owned_address(session, user.id, address_id)
    if payload.is_default:
        await session.execute(
            update(CustomerAddress)
            .where(CustomerAddress.user_id == user.id, CustomerAddress.id != address.id)
            .values(is_default=False)
        )
    for field, value in payload.model_dump().items():
        setattr(address, field, value)
    await session.commit()
    await session.refresh(address)
    return address


@router.delete("/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(address_id: UUID, session: DbSession, user: CurrentUser):
    address = await owned_address(session, user.id, address_id)
    if await session.scalar(select(Order.id).where(Order.address_id == address.id).limit(1)):
        raise HTTPException(
            status_code=409,
            detail="This address is linked to an existing order and cannot be deleted",
        )
    was_default = address.is_default
    await session.delete(address)
    await session.flush()
    if was_default:
        replacement = await session.scalar(
            select(CustomerAddress)
            .where(CustomerAddress.user_id == user.id)
            .order_by(CustomerAddress.updated_at.desc())
            .limit(1)
        )
        if replacement:
            replacement.is_default = True
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
