# app/services/pricing_service.py
import logging
from datetime import date, datetime, timedelta, UTC
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import transaction
from app.models.item import Item, ItemCategory
from app.models.pricing import PriceRecord, PricingMethod, PricingSource
from app.models.container import Container
from app.models.user import User, UserRole
from app.services.fx_service import FXRateUnavailable, FXService
from app.utils.money import quantize, to_decimal
from app.utils.pricing_math import Comparable, PricingPolicy, error_metrics, recommend_price
from app.schemas.pricing import (
    MarketPrice,
    PriceRecordCreate,
    PricingRequest,
    PricingResponse,
)

logger = logging.getLogger(__name__)


def _scraped_price(raw: Any) -> Decimal:
    """A scraped price becomes exact decimal money; garbage (zero, negative, NaN) is rejected."""
    price = quantize(to_decimal(raw), 4)
    if price <= 0:
        raise ValueError(f"Scraped price must be positive, got {raw!r}")
    return price


class PricingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Main pricing generation
    # ------------------------------------------------------------------
    async def get_item_for_user(self, item_id: int, current_user: User) -> Optional[Item]:
        """The item, only if this user may see it: same tenant, not deleted,
        and (for clerks) in one of their own containers."""
        q = select(Item).where(
            Item.id == item_id,
            Item.tenant_id == current_user.tenant_id,
            Item.deleted_at.is_(None),
        )
        if current_user.role == UserRole.CLERK:
            q = q.join(Container, Container.id == Item.container_id).where(
                Container.owner_id == current_user.id
            )
        return (await self.db.execute(q)).scalar_one_or_none()

    async def generate_pricing(
        self,
        item_id: int,
        req: PricingRequest,
        current_user: User,
    ) -> PricingResponse:
        item = await self.get_item_for_user(item_id, current_user)
        if not item:
            raise ValueError(f"Item {item_id} not found")

        # Base cost: landed cost once allocated, otherwise the purchase price (with a warning)
        unallocated_cost = not item.landed_cost or item.landed_cost <= 0
        base_cost = item.purchase_price_usd if unallocated_cost else item.landed_cost

        response = PricingResponse(
            item_id=item_id,
            landed_cost=quantize(base_cost),
            generated_at=datetime.now(UTC),
        )
        margin = req.profit_margin or settings.DEFAULT_PROFIT_MARGIN
        if req.include_cost_based:
            response.cost_based_price = quantize(base_cost * (Decimal(1) + to_decimal(margin)), 2)
            response.profit_margin = margin

        notes: list[str] = []
        comps: list[Comparable] = []

        if req.include_market_pricing:
            market, market_comps, skipped = await self._get_market_comparables(item, req.sources)
            response.market_prices = market
            comps.extend(market_comps)
            notes.extend(skipped)

        if req.include_last_sold:
            own = await self._get_own_sale_comparables(item)
            comps.extend(own)
            if own:
                response.last_sold_price = own[0].price_usd          # newest first

        policy = PricingPolicy(
            target_margin=to_decimal(margin),
            min_margin=to_decimal(settings.PRICING_MIN_MARGIN),
            half_life_days=settings.PRICING_HALF_LIFE_DAYS,
        )
        rec = recommend_price(base_cost, comps, policy)

        response.recommended_price = rec.recommended
        response.price_low         = rec.low
        response.price_high        = rec.high
        response.confidence        = rec.confidence
        response.expected_margin   = rec.expected_margin
        response.comparables_used  = rec.comps_used
        response.warnings          = ([ "Costs are not allocated yet: pricing from the purchase price. "
                                        "Run cost allocation for an accurate recommendation." ]
                                      if unallocated_cost else []) + rec.warnings + notes
        response.explanation       = rec.explanation

        # Persist recommendation
        async with transaction(self.db):
            item.recommended_price = rec.recommended
        return response

    # ------------------------------------------------------------------
    # Market prices
    # ------------------------------------------------------------------
    async def _get_market_comparables(
        self, item: Item, sources: Optional[list[PricingSource]]
    ) -> tuple[list[MarketPrice], list[Comparable], list[str]]:
        """Recent market prices for this item, converted to USD (they come in NGN, EUR, CZK...).
        Comparing raw numbers across currencies was the original bug."""
        now = datetime.now(UTC)
        q = select(PriceRecord).where(
            PriceRecord.item_id   == item.id,
            PriceRecord.tenant_id == item.tenant_id,
            PriceRecord.method    == PricingMethod.MARKET_BASED,
            PriceRecord.is_active == True,   # noqa: E712
            PriceRecord.created_at >= now - timedelta(days=settings.PRICING_MAX_COMP_AGE_DAYS),
        )
        if sources:
            q = q.where(PriceRecord.source.in_(sources))
        records = (await self.db.execute(q.order_by(PriceRecord.created_at.desc()).limit(50))).scalars().all()

        fx, rates, missing = FXService(), {}, set()
        market: list[MarketPrice] = []
        comps: list[Comparable] = []
        for r in records:
            cur = (r.currency or "USD").upper()
            if cur not in rates and cur not in missing:
                try:
                    rates[cur] = await fx.get_fx_rate(cur, "USD")
                except FXRateUnavailable:
                    missing.add(cur)
            if cur in missing:
                continue
            created = r.created_at if r.created_at.tzinfo else r.created_at.replace(tzinfo=UTC)
            age = max((now - created).total_seconds() / 86400, 0.0)
            usd = quantize(to_decimal(r.price) * rates[cur], 2)
            conf = float(r.confidence_score) if r.confidence_score is not None else 0.5
            market.append(MarketPrice(
                source=r.source, price=r.price, currency=cur, url=r.source_url,
                confidence=conf, found_at=created, price_usd=usd, age_days=round(age, 1),
            ))
            comps.append(Comparable(usd, age, r.source.value if r.source else "unknown", conf))
        notes = [f"Skipped market prices in {c}: no exchange rate available." for c in sorted(missing)]
        return market[:10], comps, notes

    async def _get_own_sale_comparables(self, item: Item) -> list[Comparable]:
        """This organisation's completed sales of similar items (same category and condition).
        Tenant-scoped: the old query read other organisations' sale prices."""
        rows = (
            await self.db.execute(
                select(Item.selling_price, Item.sold_date)
                .where(
                    Item.tenant_id == item.tenant_id,
                    Item.category  == item.category,
                    Item.condition == item.condition,
                    Item.sold      == True,          # noqa: E712
                    Item.selling_price.isnot(None),
                    Item.sold_date.isnot(None),
                    Item.id != item.id,
                    Item.deleted_at.is_(None),
                )
                .order_by(Item.sold_date.desc())
                .limit(20)
            )
        ).all()
        today = date.today()
        return [
            Comparable(quantize(price, 2), max((today - sold).days, 0), "own_sale", 1.0, own_sale=True)
            for price, sold in rows
        ]

    async def accuracy(self, tenant_id: int) -> dict[str, float]:
        """Backtest: recommended price vs what the item actually sold for."""
        rows = (
            await self.db.execute(
                select(Item.recommended_price, Item.selling_price).where(
                    Item.tenant_id == tenant_id,
                    Item.sold == True,               # noqa: E712
                    Item.recommended_price.isnot(None),
                    Item.selling_price.isnot(None),
                    Item.deleted_at.is_(None),
                )
            )
        ).all()
        return error_metrics([(r, s) for r, s in rows])

    # ------------------------------------------------------------------
    # Price record creation
    # ------------------------------------------------------------------
    async def create_price_record(
        self, data: PriceRecordCreate, current_user: User
    ) -> Optional[PriceRecord]:
        # The item must belong to the caller (tenant, and clerks: own containers)
        if not await self.get_item_for_user(data.item_id, current_user):
            return None
        user_id, tenant_id = current_user.id, current_user.tenant_id
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
                price=_scraped_price(price_data["price"]),
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
            role = UserRole.ADMIN   # background job acts for the whole tenant
        resp = await self.generate_pricing(item_id, req, _SystemUser())   # type: ignore
        return {"status": "success", "recommended_price": resp.recommended_price}

    async def fetch_market_prices_async(
        self, item_id: int, user_id: int, tenant_id: int
    ) -> None:
        """
        Background trigger called from router BackgroundTasks.
        Enqueues Celery task rather than running inline.
        Was missing before — routers were calling this directly.
        """
        from app.workers.pricing_worker import fetch_market_prices
        fetch_market_prices.apply_async(
            args=[item_id, user_id, tenant_id],
            queue="scraping_queue",
        )
        logger.info("Enqueued market price fetch: item_id=%d", item_id)