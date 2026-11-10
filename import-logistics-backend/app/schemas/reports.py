# app/schemas/reports.py
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.types import Money


# ------------------------------------------------------------------------------
# Shared filters — now wired to router query params (was unused before)
# ------------------------------------------------------------------------------
class ReportFilters(BaseModel):
    start_date:    Optional[date]       = None
    end_date:      Optional[date]       = None
    container_ids: Optional[List[int]]  = None
    categories:    Optional[List[str]]  = None
    sold_only:     bool                 = False


# ------------------------------------------------------------------------------
# Item profit report
# ------------------------------------------------------------------------------
class ProfitReportItem(BaseModel):
    item_id:            int
    item_name:          str
    category:           str
    purchase_price_usd: Money
    allocated_cost:     Money
    landed_cost:        Money
    selling_price:      Optional[Money] = None
    profit_amount:      Optional[Money] = None
    profit_margin:      Optional[float] = None
    sold:               bool
    sold_date:          Optional[date]  = None


# ------------------------------------------------------------------------------
# Container profit report
# ------------------------------------------------------------------------------
class ContainerReport(BaseModel):
    container_id:   int
    container_name: str
    container_type: str
    total_expenses: Money
    total_items:    int
    items_sold:     int
    total_cost:     Money            # landed cost of ALL items
    cost_of_goods_sold: Money        # landed cost of SOLD items
    inventory_value:    Money        # landed cost of UNSOLD items
    unallocated_expenses: Money      # expenses not yet spread over items (run allocation)
    total_revenue:  Money
    total_profit:   Money            # revenue - cost_of_goods_sold
    profit_margin:  float            # profit / cost_of_goods_sold
    created_at:     datetime


# ------------------------------------------------------------------------------
# Category profit report — powered by SQL GROUP BY (not Python grouping)
# ------------------------------------------------------------------------------
class CategoryReport(BaseModel):
    category:         str
    total_items:      int
    items_sold:       int
    total_investment: Money          # landed cost of ALL items
    cost_of_goods_sold: Money        # landed cost of SOLD items
    inventory_value:    Money        # landed cost of UNSOLD items
    total_revenue:    Money
    total_profit:     Money          # revenue - cost_of_goods_sold
    average_margin:   float
    avg_sale_price:   Optional[Money] = None


# ------------------------------------------------------------------------------
# FX impact report
# ------------------------------------------------------------------------------
class FXImpactReport(BaseModel):
    currency_pair:     str
    total_exposure:    float
    fx_gain_loss:      float
    impact_percentage: float


# ------------------------------------------------------------------------------
# Dashboard summary — cached in Redis (5 min TTL)
# ------------------------------------------------------------------------------
class DashboardSummary(BaseModel):
    active_containers:  int
    total_items:        int
    items_sold:         int
    total_revenue:      Money
    cost_of_goods_sold: Money
    inventory_value:    Money
    total_profit:       Money        # revenue - cost_of_goods_sold
    avg_profit_margin:  float
    pending_shipments:  int
    low_stock_alerts:   int
    generated_at:       datetime


# ------------------------------------------------------------------------------
# Demand analytics snapshot
# ------------------------------------------------------------------------------
class DemandSnapshot(BaseModel):
    item_category:    str
    avg_market_price: Optional[float] = None
    avg_sale_price:   Optional[float] = None
    avg_margin:       Optional[float] = None
    demand_score:     Optional[float] = None
    units_sold_30d:   int
    units_sold_90d:   int
    updated_at:       Optional[datetime] = None