# app/services/pricing_service.py
import logging
from datetime import datetime, UTC
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import transaction
from app.models.item import Item, ItemCategory
from app.models.pricing import PriceRecord, PricingMethod, PricingSource
from app.models.user import User
from app.schemas.pricing import (
    MarketPrice,
    PriceRecordCreate,
    PricingRequest,
    PricingResponse,
)

logger = logging.getLogger(__name__)


class PricingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Main pricing generation
    # ------------------------------------------------------------------
    async def generate_pricing(
        self,
        item_id: int,
        req: PricingRequest,
        current_user: User,
    ) -> PricingResponse:
        result = await self.db.execute(
            select(Item).where(
                Item.id == item_id,
                Item.tenant_id == current_user.tenant_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise ValueError(f"Item {item_id} not found")

        response = PricingResponse(
            item_id=item_id,
            landed_cost=item.landed_cost,
            generated_at=datetime.now(UTC),
        )

        if req.include_cost_based:
            margin = req.profit_margin or settings.DEFAULT_PROFIT_MARGIN
            response.cost_based_price = item.landed_cost * (1 + margin)
            response.profit_margin    = margin

        if req.include_market_pricing:
            response.market_prices = await self._get_recent_market_prices(
                item_id, req.sources
            )

        if req.include_last_sold:
            response.last_sold_price = await self._get_last_sold_price(item)

        response.recommended_price = self._calculate_recommended_price(response)

        # Persist recommendation
        if response.recommended_price:
            async with transaction(self.db):
                item.recommended_price = response.recommended_price

        return response

    # ------------------------------------------------------------------
    # Market prices
    # ------------------------------------------------------------------
    async def _get_recent_market_prices(
        self,
        item_id: int,
        sources: Optional[list[PricingSource]],
    ) -> list[MarketPrice]:
        q = select(PriceRecord).where(
            PriceRecord.item_id == item_id,
            PriceRecord.method  == PricingMethod.MARKET_BASED,
            PriceRecord.is_active == True,   # noqa: E712
        )
        if sources:
            q = q.where(PriceRecord.source.in_(sources))

        result = await self.db.execute(
            q.order_by(PriceRecord.created_at.desc()).limit(10)
        )
        records = result.scalars().all()

        return [
            MarketPrice(
                source=r.source,
                price=r.price,
                currency=r.currency,
                url=r.source_url,
                confidence=r.confidence_score or 0.5,
                found_at=r.created_at,
            )
            for r in records
        ]

    async def _get_last_sold_price(self, item: Item) -> Optional[float]:
        """
        Find the most recent sale price for a similar item
        (same category + condition). Uses proper Date ordering — was String before.
        """
        result = await self.db.execute(
            select(Item)
            .where(
                Item.category  == item.category,
                Item.condition == item.condition,
                Item.sold      == True,          # noqa: E712
                Item.selling_price.isnot(None),
                Item.id != item.id,
                Item.deleted_at.is_(None),
            )
            .order_by(Item.sold_date.desc())     # fixed: Date column — sorts correctly
            .limit(1)
        )
        similar = result.scalar_one_or_none()
        return similar.selling_price if similar else None

    def _calculate_recommended_price(
        self, resp: PricingResponse
    ) -> Optional[float]:
        prices: list[float] = []

        if resp.cost_based_price:
            prices.append(resp.cost_based_price)

        if resp.market_prices:
            total_conf = sum(p.confidence for p in resp.market_prices)
            if total_conf > 0:
                weighted = sum(
                    p.price * p.confidence for p in resp.market_prices
                ) / total_conf
                prices.append(weighted)

        if resp.last_sold_price:
            prices.append(resp.last_sold_price)

        return round(sum(prices) / len(prices), 2) if prices else None

    # ------------------------------------------------------------------
    # Price record creation
    # ------------------------------------------------------------------
    async def create_price_record(
        self, data: PriceRecordCreate, user_id: int, tenant_id: int
    ) -> PriceRecord:
        async with transaction(self.db):
            record = PriceRecord(
                tenant_id=tenant_id,
                item_id=data.item_id,
                user_id=user_id,
                method=data.method,
                source=data.source,
                price=data.price,
                currency=data.currency,
                margin_percentage=data.margin_percentage,
                notes=data.notes,
            )
            self.db.add(record)
        await self.db.refresh(record)
        return record

    async def create_market_price_record(
        self,
        item_id: int,
        source: str,
        price_data: dict[str, Any],
        user_id: int,
        tenant_id: int,
    ) -> PriceRecord:
        """Called by pricing_worker after scraping — was missing before."""
        async with transaction(self.db):
            record = PriceRecord(
                tenant_id=tenant_id,
                item_id=item_id,
                user_id=user_id,
                method=PricingMethod.MARKET_BASED,
                source=PricingSource(source),
                price=price_data["price"],
                currency=price_data.get("currency", "USD"),
                source_url=price_data.get("url"),
                source_data=price_data,
                confidence_score=price_data.get("confidence", 0.5),
                is_active=True,
            )
            self.db.add(record)
        await self.db.refresh(record)
        return record

    async def get_price_history(
        self, item_id: int, current_user: User
    ) -> list[PriceRecord]:
        """Was missing before."""
        result = await self.db.execute(
            select(PriceRecord)
            .where(
                PriceRecord.item_id   == item_id,
                PriceRecord.tenant_id == current_user.tenant_id,
            )
            .order_by(PriceRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def calculate_recommended_price(self, item_id: int) -> dict[str, Any]:
        """Called by update_item_pricing worker — was missing before."""
        result = await self.db.execute(select(Item).where(Item.id == item_id))
        item = result.scalar_one_or_none()
        if not item:
            return {"status": "error", "message": "Item not found"}

        req = PricingRequest(
            include_cost_based=True,
            include_market_pricing=True,
            include_last_sold=True,
        )
        # Use a dummy user context — worker does not have a user session
        class _SystemUser:
            tenant_id = item.tenant_id
        resp = await self.generate_pricing(item_id, req, _SystemUser())   # type: ignore
        return {"status": "success", "recommended_price": resp.recommended_price}

    async def fetch_market_prices_async(
        self, item_id: int, user_id: int
    ) -> None:
        """
        Background trigger called from router BackgroundTasks.
        Enqueues Celery task rather than running inline.
        Was missing before — routers were calling this directly.
        """
        from app.workers.pricing_worker import fetch_market_prices
        fetch_market_prices.apply_async(
            args=[item_id, user_id],
            queue="pricing_queue",
        )
        logger.info("Enqueued market price fetch: item_id=%d", item_id)