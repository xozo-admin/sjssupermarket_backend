from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_products() -> dict[str, list[object]]:
    """Temporary endpoint; connect the catalog repository next."""
    return {"items": []}
