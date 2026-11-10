# app/routers/reports.py
# Fixed: import path was app.api.deps — now app.routers.deps
# Fixed: category report now uses SQL GROUP BY, not Python grouping
# Fixed: container report no longer does N+1 per-container queries
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.routers.deps import CurrentUser, DBDep, ManagerUser
from app.models.container import Container
from app.models.expense import ContainerExpense
from app.models.item import Item, ItemCategory
from app.models.warehouse import Warehouse, WarehouseInventory
from app.utils.money import quantize
from app.utils.reporting import profit_and_margin, unallocated
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

    # Visibility policy (same as the container and item lists): a CLERK sees only the containers
    # they own, and therefore only the totals of those containers. Everyone else sees the whole
    # organisation. Organisation-wide stock levels are not a clerk's data, so they get 0 there.
    is_clerk = current_user.role == UserRole.CLERK
    scope = [Container.owner_id == current_user.id] if is_clerk else []

    container_q = select(func.count(Container.id)).where(
        Container.tenant_id == tenant_id,
        Container.deleted_at.is_(None),
        *scope,
    )
    active_containers = (await db.execute(container_q)).scalar_one()

    sold = Item.sold == True        # noqa: E712
    items_q = (
        select(
            func.count(Item.id),
            func.count(Item.id).filter(sold),
            func.coalesce(func.sum(Item.selling_price).filter(sold), 0),
            func.coalesce(func.sum(Item.landed_cost).filter(sold), 0),
            func.coalesce(func.sum(Item.landed_cost).filter(~sold), 0),
        )
        .select_from(Item)
        .join(Container, Container.id == Item.container_id)
        .where(
            Item.tenant_id == tenant_id,
            Item.deleted_at.is_(None),
            Container.deleted_at.is_(None),     # items of a deleted container no longer count
            *scope,
        )
    )

    total_items, items_sold, revenue, cogs, inventory = (await db.execute(items_q)).one()
    total_profit, avg_margin = profit_and_margin(revenue, cogs)

    shipments_q = select(func.count(Container.id)).where(
        Container.tenant_id == tenant_id,
        Container.is_shipped == True,          # noqa: E712
        Container.deleted_at.is_(None),
        *scope,
    )
    pending_shipments = (await db.execute(shipments_q)).scalar_one()

    # Low stock: ONLY this organisation's warehouses (this query used to count every tenant's rows)
    low_stock_q = (
        select(func.count(WarehouseInventory.id))
        .join(Warehouse, Warehouse.id == WarehouseInventory.warehouse_id)
        .where(
            Warehouse.tenant_id == tenant_id,
            WarehouseInventory.quantity <= WarehouseInventory.min_quantity,
            WarehouseInventory.min_quantity > 0,
        )
    )
    low_stock = 0 if is_clerk else (await db.execute(low_stock_q)).scalar_one()

    summary = DashboardSummary(
        active_containers=active_containers,
        total_items=total_items,
        items_sold=items_sold,
        total_revenue=quantize(revenue),
        cost_of_goods_sold=quantize(cogs),
        inventory_value=quantize(inventory),
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
    q = select(Item).join(Container, Container.id == Item.container_id).where(
        Item.tenant_id  == current_user.tenant_id,
        Item.deleted_at.is_(None),
        Container.deleted_at.is_(None),
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
            profit_amount=quantize(i.selling_price - i.landed_cost)
                          if i.selling_price is not None and i.landed_cost else None,
            profit_margin=float(quantize((i.selling_price - i.landed_cost) / i.landed_cost, 6))
                          if i.selling_price is not None and i.landed_cost else None,
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
    tid  = current_user.tenant_id
    sold = Item.sold == True        # noqa: E712

    # Expenses and items are aggregated SEPARATELY, then joined 1:1 per container.
    # (Joining both tables to containers multiplied every total by the other's row count.)
    exp_sq = (
        select(
            ContainerExpense.container_id.label("cid"),
            func.sum(ContainerExpense.amount_usd).label("total_expenses"),
        )
        .where(ContainerExpense.tenant_id == tid)
        .group_by(ContainerExpense.container_id)
        .subquery()
    )
    item_sq = (
        select(
            Item.container_id.label("cid"),
            func.count(Item.id).label("total_items"),
            func.count(Item.id).filter(sold).label("items_sold"),
            func.sum(Item.landed_cost).label("total_cost"),
            func.sum(Item.landed_cost).filter(sold).label("cogs"),
            func.sum(Item.landed_cost).filter(~sold).label("inventory"),
            func.sum(Item.selling_price).filter(sold).label("revenue"),
            func.sum(Item.allocated_cost).label("allocated"),
        )
        .where(Item.tenant_id == tid, Item.deleted_at.is_(None))
        .group_by(Item.container_id)
        .subquery()
    )
    q = (
        select(
            Container.id, Container.name, Container.container_type, Container.created_at,
            exp_sq.c.total_expenses, item_sq.c.total_items, item_sq.c.items_sold,
            item_sq.c.total_cost, item_sq.c.cogs, item_sq.c.inventory,
            item_sq.c.revenue, item_sq.c.allocated,
        )
        .select_from(Container)
        .outerjoin(exp_sq, exp_sq.c.cid == Container.id)
        .outerjoin(item_sq, item_sq.c.cid == Container.id)
        .where(Container.tenant_id == tid, Container.deleted_at.is_(None))
        .order_by(Container.id)
    )
    if owner_id:
        q = q.where(Container.owner_id == owner_id)

    reports = []
    for row in (await db.execute(q)).all():
        profit, margin = profit_and_margin(row.revenue, row.cogs)
        reports.append(ContainerReport(
            container_id=row.id,
            container_name=row.name,
            container_type=row.container_type.value,
            total_expenses=quantize(row.total_expenses or 0),
            total_items=row.total_items or 0,
            items_sold=row.items_sold or 0,
            total_cost=quantize(row.total_cost or 0),
            cost_of_goods_sold=quantize(row.cogs or 0),
            inventory_value=quantize(row.inventory or 0),
            unallocated_expenses=unallocated(row.total_expenses, row.allocated),
            total_revenue=quantize(row.revenue or 0),
            total_profit=profit,
            profit_margin=margin,
            created_at=row.created_at,
        ))
    return reports


@router.get(
    "/profit/categories",
    response_model=list[CategoryReport],
    summary="Per-category profit report - SQL GROUP BY",
)
async def get_category_reports(db: DBDep, current_user: CurrentUser):
    sold = Item.sold == True        # noqa: E712
    q = (
        select(
            Item.category,
            func.count(Item.id).label("total_items"),
            func.count(Item.id).filter(sold).label("items_sold"),
            func.coalesce(func.sum(Item.landed_cost), 0).label("total_investment"),
            func.coalesce(func.sum(Item.landed_cost).filter(sold), 0).label("cogs"),
            func.coalesce(func.sum(Item.landed_cost).filter(~sold), 0).label("inventory"),
            func.coalesce(func.sum(Item.selling_price).filter(sold), 0).label("revenue"),
            func.avg(Item.selling_price).filter(sold).label("avg_sale_price"),
        )
        .join(Container, Container.id == Item.container_id)
        .where(Item.tenant_id == current_user.tenant_id, Item.deleted_at.is_(None),
               Container.deleted_at.is_(None))
        .group_by(Item.category)
        .order_by(Item.category)
    )
    if current_user.role == UserRole.CLERK:
        q = q.where(Container.owner_id == current_user.id)

    out = []
    for row in (await db.execute(q)).all():
        profit, margin = profit_and_margin(row.revenue, row.cogs)
        out.append(CategoryReport(
            category=row.category.value,
            total_items=row.total_items,
            items_sold=row.items_sold,
            total_investment=quantize(row.total_investment),
            cost_of_goods_sold=quantize(row.cogs),
            inventory_value=quantize(row.inventory),
            total_revenue=quantize(row.revenue),
            total_profit=profit,
            average_margin=margin,
            avg_sale_price=quantize(row.avg_sale_price) if row.avg_sale_price is not None else None,
        ))
    return out


@router.get(
    "/demand",
    response_model=list[DemandSnapshot],
    summary="Demand analytics per category",
)
async def get_demand_analytics(db: DBDep, current_user: CurrentUser):
    from app.models.analytics import DemandAnalytics
    if current_user.role == UserRole.CLERK:
        # These figures are organisation-wide and cannot be narrowed to a clerk's own containers
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation-wide demand analytics are not available to clerks",
        )
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