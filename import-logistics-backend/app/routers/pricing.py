# app/routers/pricing.py
from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.routers.deps import ClerkUser, CurrentUser, DBDep, ManagerUser
from app.schemas.pricing import (
    PriceRecordCreate,
    PriceRecordInDB,
    PricingAccuracy,
    PricingRequest,
    PricingResponse,
)
from app.services.pricing_service import PricingService

router = APIRouter()


@router.post(
    "/generate/{item_id}",
    response_model=PricingResponse,
    summary="Generate pricing recommendation for an item",
)
async def generate_pricing(
    item_id: int,
    data: PricingRequest,
    background_tasks: BackgroundTasks,
    db: DBDep,
    current_user: ClerkUser,   # it SAVES the recommended price on the item: viewers are read-only
):
    svc = PricingService(db)

    try:
        response = await svc.generate_pricing(item_id, data, current_user)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    # Only after we know the item is the caller's: enqueue market scraping
    if data.include_market_pricing:
        background_tasks.add_task(
            svc.fetch_market_prices_async, item_id, current_user.id, current_user.tenant_id
        )
    return response


@router.post(
    "/refresh-market/{item_id}",
    summary="Trigger market price refresh for an item (async)",
)
async def refresh_market_pricing(
    item_id: int,
    background_tasks: BackgroundTasks,
    db: DBDep,
    current_user: ClerkUser,   # it starts scraping external sites: viewers are read-only
):
    svc = PricingService(db)
    if not await svc.get_item_for_user(item_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    background_tasks.add_task(
        svc.fetch_market_prices_async, item_id, current_user.id, current_user.tenant_id
    )
    return {"message": "Market price refresh queued", "item_id": item_id}


@router.post(
    "/record",
    response_model=PriceRecordInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Manually create a price record",
)
async def create_price_record(
    data: PriceRecordCreate, db: DBDep, current_user: ClerkUser
):
    svc = PricingService(db)
    record = await svc.create_price_record(data, current_user)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return record


@router.get(
    "/item/{item_id}",
    response_model=list[PriceRecordInDB],
    summary="Get full price history for an item",
)
async def get_price_history(item_id: int, db: DBDep, current_user: CurrentUser):
    svc = PricingService(db)
    if not await svc.get_item_for_user(item_id, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return await svc.get_price_history(item_id, current_user)


@router.get(
    "/accuracy",
    response_model=PricingAccuracy,
    summary="How accurate recommendations were vs actual sale prices (manager+)",
)
async def pricing_accuracy(db: DBDep, current_user: ManagerUser):
    return await PricingService(db).accuracy(current_user.tenant_id)
