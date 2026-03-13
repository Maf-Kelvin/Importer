# app/services/pricing_service.py
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.item import Item
from app.models.pricing import PriceRecord, PricingMethod, PricingSource
from app.schemas.pricing import PricingRequest, PricingResponse, MarketPrice, PriceRecordCreate
from app.core.config import settings
from datetime import datetime
import json


class PricingService:
    def __init__(self, db: Session):
        self.db = db
    
    def generate_pricing(self, item_id: int, pricing_request: PricingRequest, current_user) -> PricingResponse:
        """Generate pricing recommendations for an item."""
        item = self.db.query(Item).filter(Item.id == item_id).first()
        if not item:
            raise ValueError("Item not found")
        
        response = PricingResponse(
            item_id=item_id,
            generated_at=datetime.utcnow().isoformat()
        )
        
        # Cost-based pricing
        if pricing_request.include_cost_based:
            margin = pricing_request.profit_margin or settings.DEFAULT_PROFIT_MARGIN
            response.cost_based_price = item.landed_cost * (1 + margin)
            response.profit_margin = margin
        
        # Market-based pricing (from stored records)
        if pricing_request.include_market_pricing:
            market_prices = self._get_recent_market_prices(item_id, pricing_request.sources)
            response.market_prices = market_prices
        
        # Last sold price
        if pricing_request.include_last_sold:
            last_sold = self._get_last_sold_price(item)
            response.last_sold_price = last_sold
        
        # Calculate recommended price
        response.recommended_price = self._calculate_recommended_price(response)
        
        return response
    
    def _get_recent_market_prices(self, item_id: int, sources: Optional[List[PricingSource]]) -> List[MarketPrice]:
        """Get recent market prices for item."""
        query = self.db.query(PriceRecord).filter(
            PriceRecord.item_id == item_id,
            PriceRecord.method == PricingMethod.MARKET_BASED,
            PriceRecord.is_active == True
        )
        
        if sources:
            query = query.filter(PriceRecord.source.in_(sources))
        
        records = query.order_by(PriceRecord.created_at.desc()).limit(10).all()
        
        return [
            MarketPrice(
                source=record.source,
                price=record.price,
                currency=record.currency,
                url=record.source_url,
                confidence=record.confidence_score or 0.5,
                found_at=record.created_at.isoformat()
            )
            for record in records
        ]
    
    def _get_last_sold_price(self, item: Item) -> Optional[float]:
        """Get last sold price for similar items."""
        # Find similar items that were sold
        similar_sold = self.db.query(Item).filter(
            Item.category == item.category,
            Item.condition == item.condition,
            Item.sold == True,
            Item.selling_price.isnot(None)
        ).order_by(Item.sold_date.desc()).first()
        
        return similar_sold.selling_price if similar_sold else None
    
    def _calculate_recommended_price(self, pricing_response: PricingResponse) -> Optional[float]:
        """Calculate recommended price based on available data."""
        prices = []
        
        if pricing_response.cost_based_price:
            prices.append(pricing_response.cost_based_price)
        
        if pricing_response.market_prices:
            # Weight market prices by confidence
            market_avg = sum(p.price * p.confidence for p in pricing_response.market_prices) / \
                        sum(p.confidence for p in pricing_response.market_prices)
            prices.append(market_avg)
        
        if pricing_response.last_sold_price:
            prices.append(pricing_response.last_sold_price)
        
        return sum(prices) / len(prices) if prices else None
    
    def create_price_record(self, price_record: PriceRecordCreate, user_id: int) -> PriceRecord:
        """Create a manual price record."""
        record = PriceRecord(
            item_id=price_record.item_id,
            user_id=user_id,
            method=price_record.method,
            source=price_record.source,
            price=price_record.price,
            currency=price_record.currency,
            margin_percentage=price_record.margin_percentage,
            notes=price_record.notes
        )
        
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record