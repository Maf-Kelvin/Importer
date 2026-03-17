# app/routers/reports.py
# Fixed: import path was app.api.deps — now app.routers.deps
# Fixed: category report now uses SQL GROUP BY, not Python grouping
# Fixed: container report no longer does N+1 per-container queries
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.deps import CurrentUser, DBDep, ManagerUser
from app.models.container import Container
from app.models.expense import ContainerExpense
from app.models.item import Item, ItemCategory
from app.models.user import UserRole
from app.schemas.reports import (
    CategoryReport,
    ContainerReport,
    DashboardSummary,
    DemandSnapshot,
    ProfitReportItem,
    ReportFilters,
)

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=DashboardSummary,
    summary="Dashboard summary metrics (Redis-cached 5 min)",
)
async def get_dashboard(db: DBDep, current_user: CurrentUser):
    from app.services.cache_service import CacheService
    from datetime import datetime, UTC

    cache     = CacheService()
    cache_key = f"dashboard:{current_user.tenant_id}:{current_user.id}"

    cached = await cache.get(cache_key, DashboardSummary)
    if cached:
        return cached

    tenant_id = current_user.tenant_id

    # Single-pass aggregation queries
    container_q = select(func.count(Container.id)).where(
        Container.tenant_id == tenant_id,
        Container.deleted_at.is_(None),
    )
    active_containers = (await db.execute(container_q)).scalar_one()

    items_q = select(
        func.count(Item.id),
        func.count(Item.id).filter(Item.sold == True),        # noqa: E712
        func.coalesce(func.sum(Item.selling_price).filter(Item.sold == True), 0),
        func.coalesce(func.sum(Item.landed_cost), 0),
    ).where(Item.tenant_id == tenant_id, Item.deleted_at.is_(None))

    row = (await db.execute(items_q)).one()
    total_items, items_sold, total_revenue, total_cost = row
    total_profit   = float(total_revenue) - float(total_cost)
    avg_margin     = (total_profit / float(total_cost)) if total_cost else 0.0

    shipments_q = select(func.count(Container.id)).where(
        Container.tenant_id == tenant_id,
        Container.is_shipped == True,          # noqa: E712
        Container.deleted_at.is_(None),
    )
    pending_shipments = (await db.execute(shipments_q)).scalar_one()

    from app.models.warehouse import WarehouseInventory
    low_stock_q = select(func.count(WarehouseInventory.id)).where(
        WarehouseInventory.quantity <= WarehouseInventory.min_quantity,
        WarehouseInventory.min_quantity > 0,
    )
    low_stock = (await db.execute(low_stock_q)).scalar_one()

    summary = DashboardSummary(
        active_containers=active_containers,
        total_items=total_items,
        items_sold=items_sold,
        total_revenue=float(total_revenue),
        total_profit=total_profit,
        avg_profit_margin=avg_margin,
        pending_shipments=pending_shipments,
        low_stock_alerts=low_stock,
        generated_at=datetime.now(UTC),
    )

    await cache.set(cache_key, summary, ttl=300)   # 5-minute TTL
    return summary


@router.get(
    "/profit/items",
    response_model=list[ProfitReportItem],
    summary="Per-item profit report",
)
async def get_profit_report_items(
    db: DBDep,
    current_user: CurrentUser,
    container_id: Optional[int]  = Query(None),
    category:     Optional[str]  = Query(None),
    sold_only:    bool            = Query(False),
    start_date:   Optional[date] = Query(None),
    end_date:     Optional[date] = Query(None),
):
    q = select(Item).join(Container).where(
        Item.tenant_id  == current_user.tenant_id,
        Item.deleted_at.is_(None),
    )
    if current_user.role == UserRole.CLERK:
        q = q.where(Container.owner_id == current_user.id)
    if container_id:
        q = q.where(Item.container_id == container_id)
    if category:
        q = q.where(Item.category == category)
    if sold_only:
        q = q.where(Item.sold == True)             # noqa: E712
    if start_date:
        q = q.where(Item.purchase_date >= start_date)
    if end_date:
        q = q.where(Item.purchase_date <= end_date)

    result = await db.execute(q)
    items  = result.scalars().all()

    return [
        ProfitReportItem(
            item_id=i.id,
            item_name=i.name,
            category=i.category.value,
            purchase_price_usd=i.purchase_price_usd,
            allocated_cost=i.allocated_cost,
            landed_cost=i.landed_cost,
            selling_price=i.selling_price,
            profit_amount=(i.selling_price - i.landed_cost) if i.selling_price and i.landed_cost else None,
            profit_margin=((i.selling_price - i.landed_cost) / i.landed_cost)
                          if i.selling_price and i.landed_cost else None,
            sold=i.sold,
            sold_date=i.sold_date,
        )
        for i in items
    ]


@router.get(
    "/profit/containers",
    response_model=list[ContainerReport],
    summary="Per-container profit report (manager+ only)",
)
async def get_container_reports(
    db: DBDep,
    current_user: ManagerUser,
    owner_id: Optional[int] = Query(None),
):
    # Fixed: single SQL query with aggregation — was N+1 per container before
    q = (
        select(
            Container.id,
            Container.name,
            Container.container_type,
            Container.created_at,
            func.coalesce(func.sum(ContainerExpense.amount_usd), 0).label("total_expenses"),
            func.count(Item.id).label("total_items"),
            func.count(Item.id).filter(Item.sold == True).label("items_sold"),   # noqa: E712
            func.coalesce(func.sum(Item.landed_cost), 0).label("total_cost"),
            func.coalesce(
                func.sum(Item.selling_price).filter(Item.sold == True), 0   # noqa: E712
            ).label("total_revenue"),
        )
        .outerjoin(ContainerExpense, ContainerExpense.container_id == Container.id)
        .outerjoin(Item, Item.container_id == Container.id)
        .where(
            Container.tenant_id  == current_user.tenant_id,
            Container.deleted_at.is_(None),
        )
        .group_by(Container.id)
    )
    if owner_id:
        q = q.where(Container.owner_id == owner_id)

    rows   = (await db.execute(q)).all()
    reports = []
    for row in rows:
        profit        = float(row.total_revenue) - float(row.total_cost)
        profit_margin = profit / float(row.total_cost) if row.total_cost else 0.0
        reports.append(ContainerReport(
            container_id=row.id,
            container_name=row.name,
            container_type=row.container_type.value,
            total_expenses=float(row.total_expenses),
            total_items=row.total_items,
            items_sold=row.items_sold,
            total_cost=float(row.total_cost),
            total_revenue=float(row.total_revenue),
            total_profit=profit,
            profit_margin=profit_margin,
            created_at=row.created_at,
        ))
    return reports


@router.get(
    "/profit/categories",
    response_model=list[CategoryReport],
    summary="Per-category profit report — SQL GROUP BY",
)
async def get_category_reports(db: DBDep, current_user: CurrentUser):
    # Fixed: SQL GROUP BY instead of Python grouping with full table scan
    q = (
        select(
            Item.category,
            func.count(Item.id).label("total_items"),
            func.count(Item.id).filter(Item.sold == True).label("items_sold"),   # noqa: E712
            func.coalesce(func.sum(Item.landed_cost), 0).label("total_investment"),
            func.coalesce(
                func.sum(Item.selling_price).filter(Item.sold == True), 0   # noqa: E712
            ).label("total_revenue"),
            func.coalesce(
                func.avg(Item.selling_price).filter(Item.sold == True), 0   # noqa: E712
            ).label("avg_sale_price"),
        )
        .join(Container)
        .where(
            Item.tenant_id  == current_user.tenant_id,
            Item.deleted_at.is_(None),
        )
        .group_by(Item.category)
    )
    if current_user.role == UserRole.CLERK:
        q = q.where(Container.owner_id == current_user.id)

    rows = (await db.execute(q)).all()
    return [
        CategoryReport(
            category=row.category.value,
            total_items=row.total_items,
            items_sold=row.items_sold,
            total_investment=float(row.total_investment),
            total_revenue=float(row.total_revenue),
            total_profit=float(row.total_revenue) - float(row.total_investment),
            average_margin=(
                (float(row.total_revenue) - float(row.total_investment))
                / float(row.total_investment)
            ) if row.total_investment else 0.0,
            avg_sale_price=float(row.avg_sale_price) if row.avg_sale_price else None,
        )
        for row in rows
    ]


@router.get(
    "/demand",
    response_model=list[DemandSnapshot],
    summary="Demand analytics per category",
)
async def get_demand_analytics(db: DBDep, current_user: CurrentUser):
    from app.models.analytics import DemandAnalytics
    result = await db.execute(
        select(DemandAnalytics)
        .where(DemandAnalytics.tenant_id == current_user.tenant_id)
        .order_by(DemandAnalytics.demand_score.desc().nullslast())
    )
    rows = result.scalars().all()
    return [
        DemandSnapshot(
            item_category=r.item_category,
            avg_market_price=float(r.avg_market_price) if r.avg_market_price else None,
            avg_sale_price=float(r.avg_sale_price) if r.avg_sale_price else None,
            avg_margin=r.avg_margin,
            demand_score=r.demand_score,
            units_sold_30d=r.units_sold_30d,
            units_sold_90d=r.units_sold_90d,
            updated_at=r.updated_at_calc,
        )
        for r in rows
    ]