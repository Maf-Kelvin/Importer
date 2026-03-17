# app/workers/pricing_worker.py
import asyncio
import logging

from celery import current_task

from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(
    bind=True,
    name="app.workers.pricing_worker.fetch_market_prices",
    max_retries=3,
    default_retry_delay=180,   # 3 min — scraping sites may be temporarily slow
    queue="scraping_queue",
)
def fetch_market_prices(self, item_id: int, user_id: int):
    """
    Scrape market prices for an item from all configured sources
    and persist each result as a PriceRecord.
    """
    try:
        return _run(_do_fetch_market_prices(self, item_id, user_id))
    except Exception as exc:
        logger.error(
            "fetch_market_prices failed item_id=%d: %s", item_id, exc, exc_info=True
        )
        raise self.retry(exc=exc)


async def _do_fetch_market_prices(task, item_id: int, user_id: int) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.models.item import Item
    from app.services.pricing_service import PricingService
    from app.services.scraper_service import ScraperService
    from sqlalchemy import select

    sources = ["jiji", "ebay", "mobile_de", "autoscout24", "bazos_cz"]
    results = []

    async with AsyncSessionLocal() as db:
        # Load item for name + category
        item_result = await db.execute(select(Item).where(Item.id == item_id))
        item = item_result.scalar_one_or_none()
        if not item:
            logger.warning("fetch_market_prices: item_id=%d not found", item_id)
            return {"status": "error", "message": "Item not found"}

        pricing_svc = PricingService(db)
        scraper_svc = ScraperService()

        for i, source in enumerate(sources):
            # Update Celery task progress state
            current_task.update_state(
                state="PROGRESS",
                meta={"current": i + 1, "total": len(sources), "source": source},
            )

            try:
                prices = await scraper_svc.scrape_prices(
                    item_name=item.name,
                    category=item.category.value,
                    source=source,
                )
                for price_data in prices:
                    await pricing_svc.create_market_price_record(
                        item_id=item_id,
                        source=source,
                        price_data=price_data,
                        user_id=user_id,
                        tenant_id=item.tenant_id,
                    )
                results.extend(prices)
                logger.info(
                    "Scraped %d prices from %s for item_id=%d",
                    len(prices), source, item_id,
                )
            except Exception as e:
                # Per-source failure does not abort the whole task
                logger.warning(
                    "Scrape failed source=%s item_id=%d: %s", source, item_id, e
                )

    return {
        "status":          "success",
        "item_id":         item_id,
        "results_count":   len(results),
        "sources_checked": len(sources),
    }


@celery_app.task(
    bind=True,
    name="app.workers.pricing_worker.update_item_pricing",
    max_retries=3,
    default_retry_delay=60,
    queue="pricing_queue",
)
def update_item_pricing(self, item_id: int):
    """Recalculate and persist recommended price for a single item."""
    try:
        return _run(_do_update_item_pricing(item_id))
    except Exception as exc:
        logger.error(
            "update_item_pricing failed item_id=%d: %s", item_id, exc, exc_info=True
        )
        raise self.retry(exc=exc)


async def _do_update_item_pricing(item_id: int) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.pricing_service import PricingService

    async with AsyncSessionLocal() as db:
        svc = PricingService(db)
        return await svc.calculate_recommended_price(item_id)


@celery_app.task(
    bind=True,
    name="app.workers.pricing_worker.refresh_demand_analytics",
    max_retries=2,
    default_retry_delay=300,
    queue="pricing_queue",
)
def refresh_demand_analytics(self):
    """
    Recalculate demand_analytics table for all tenants.
    Runs every 6 hours via beat schedule.
    """
    try:
        return _run(_do_refresh_demand_analytics())
    except Exception as exc:
        logger.error("refresh_demand_analytics failed: %s", exc, exc_info=True)
        raise self.retry(exc=exc)


async def _do_refresh_demand_analytics() -> dict:
    from datetime import datetime, UTC, timedelta
    from sqlalchemy import func, select
    from app.core.database import AsyncSessionLocal, transaction
    from app.models.analytics import DemandAnalytics
    from app.models.item import Item, ItemCategory

    updated = 0
    async with AsyncSessionLocal() as db:
        # Aggregate sales per category per tenant over last 30 and 90 days
        now   = datetime.now(UTC)
        d30   = (now - timedelta(days=30)).date()
        d90   = (now - timedelta(days=90)).date()

        for category in ItemCategory:
            # Get all tenants that have items in this category
            tenant_result = await db.execute(
                select(Item.tenant_id)
                .where(Item.category == category)
                .distinct()
            )
            tenants = tenant_result.scalars().all()

            for tenant_id in tenants:
                base_q = select(Item).where(
                    Item.tenant_id == tenant_id,
                    Item.category  == category,
                    Item.deleted_at.is_(None),
                )
                items_result = await db.execute(base_q)
                items = items_result.scalars().all()

                if not items:
                    continue

                sold_items = [i for i in items if i.sold and i.selling_price]
                sold_30d   = [i for i in sold_items if i.sold_date and i.sold_date >= d30]
                sold_90d   = [i for i in sold_items if i.sold_date and i.sold_date >= d90]

                avg_sale = (
                    sum(i.selling_price for i in sold_items) / len(sold_items)
                    if sold_items else None
                )
                avg_margin = (
                    sum(
                        (i.selling_price - i.landed_cost) / i.landed_cost
                        for i in sold_items if i.landed_cost
                    ) / len(sold_items)
                    if sold_items else None
                )

                async with transaction(db):
                    existing = await db.execute(
                        select(DemandAnalytics).where(
                            DemandAnalytics.tenant_id     == tenant_id,
                            DemandAnalytics.item_category == category.value,
                        )
                    )
                    record = existing.scalar_one_or_none()
                    if record:
                        record.avg_sale_price  = avg_sale
                        record.avg_margin      = avg_margin
                        record.units_sold_30d  = len(sold_30d)
                        record.units_sold_90d  = len(sold_90d)
                        record.updated_at_calc = now
                    else:
                        db.add(DemandAnalytics(
                            tenant_id=tenant_id,
                            item_category=category.value,
                            avg_sale_price=avg_sale,
                            avg_margin=avg_margin,
                            units_sold_30d=len(sold_30d),
                            units_sold_90d=len(sold_90d),
                            updated_at_calc=now,
                        ))
                updated += 1

    logger.info("Demand analytics refreshed: %d category/tenant combinations", updated)
    return {"status": "success", "updated": updated}