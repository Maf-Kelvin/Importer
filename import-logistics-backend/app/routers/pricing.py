# app/routers/pricing.py
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from app.routers.deps import get_db, get_current_active_user, get_clerk_or_higher_user
from app.models.user import User
from app.schemas.pricing import PriceRecordCreate, PriceRecordInDB, PricingRequest, PricingResponse
from app.services.pricing_service import PricingService

router = APIRouter()


@router.post("/generate/{item_id}", response_model=PricingResponse)
def generate_pricing(
    item_id: int,
    pricing_request: PricingRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Generate pricing recommendations for an item."""
    pricing_service = PricingService(db)
    
    # Start background task for market pricing if requested
    if pricing_request.include_market_pricing:
        background_tasks.add_task(
            pricing_service.fetch_market_prices_async,
            item_id,
            current_user.id
        )
    
    return pricing_service.generate_pricing(item_id, pricing_request, current_user)


@router.post("/record", response_model=PriceRecordInDB)
def create_price_record(
    price_record: PriceRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Create manual price record."""
    pricing_service = PricingService(db)
    return pricing_service.create_price_record(price_record, current_user.id)


@router.get("/item/{item_id}", response_model=List[PriceRecordInDB])
def get_item_price_history(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get price history for an item."""
    pricing_service = PricingService(db)
    return pricing_service.get_price_history(item_id, current_user)


@router.post("/refresh-market/{item_id}")
def refresh_market_pricing(
    item_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Trigger market pricing refresh for an item."""
    background_tasks.add_task(
        PricingService(db).fetch_market_prices_async,
        item_id,
        current_user.id
    )
    
    return {"message": "Market pricing refresh started"}

