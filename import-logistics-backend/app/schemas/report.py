# app/schemas/reports.py
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


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
    purchase_price_usd: float
    allocated_cost:     float
    landed_cost:        float
    selling_price:      Optional[float] = None
    profit_amount:      Optional[float] = None
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
    total_expenses: float
    total_items:    int
    items_sold:     int
    total_cost:     float
    total_revenue:  float
    total_profit:   float
    profit_margin:  float
    created_at:     datetime


# ------------------------------------------------------------------------------
# Category profit report — powered by SQL GROUP BY (not Python grouping)
# ------------------------------------------------------------------------------
class CategoryReport(BaseModel):
    category:         str
    total_items:      int
    items_sold:       int
    total_investment: float
    total_revenue:    float
    total_profit:     float
    average_margin:   float
    avg_sale_price:   Optional[float] = None


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
    total_revenue:      float
    total_profit:       float
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