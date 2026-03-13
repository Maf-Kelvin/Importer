# app/schemas/reports.py
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class ProfitReportItem(BaseModel):
    item_id: int
    item_name: str
    category: str
    purchase_price_usd: float
    landed_cost: float
    selling_price: Optional[float] = None
    profit_amount: Optional[float] = None
    profit_margin: Optional[float] = None
    sold: bool


class ContainerReport(BaseModel):
    container_id: int
    container_name: str
    total_expenses: float
    total_items: int
    items_sold: int
    total_revenue: float
    total_profit: float
    profit_margin: float


class CategoryReport(BaseModel):
    category: str
    total_items: int
    items_sold: int
    total_investment: float
    total_revenue: float
    total_profit: float
    average_margin: float


class FXImpactReport(BaseModel):
    currency_pair: str
    total_exposure: float
    fx_gain_loss: float
    impact_percentage: float


class ReportFilters(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    container_ids: Optional[List[int]] = None
    categories: Optional[List[str]] = None
    sold_only: bool = False