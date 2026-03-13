# app/api/v1/reports.py
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app.api.deps import get_db, get_current_active_user, get_manager_or_admin_user
from app.models.user import User, UserRole
from app.models.container import Container
from app.models.item import Item, ItemCategory
from app.models.expense import ContainerExpense
from app.schemas.reports import (
    ProfitReportItem, ContainerReport, CategoryReport, 
    FXImpactReport, ReportFilters
)
from datetime import datetime

router = APIRouter()


@router.get("/profit/items", response_model=List[ProfitReportItem])
def get_profit_report_items(
    container_id: Optional[int] = None,
    category: Optional[str] = None,
    sold_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get profit report for items."""
    query = db.query(Item).join(Container)
    
    # Role-based filtering
    if current_user.role == UserRole.CLERK:
        query = query.filter(Container.owner_id == current_user.id)
    
    # Apply filters
    if container_id:
        query = query.filter(Item.container_id == container_id)
    
    if category:
        query = query.filter(Item.category == category)
    
    if sold_only:
        query = query.filter(Item.sold == True)
    
    items = query.all()
    
    profit_items = []
    for item in items:
        profit_amount = None
        profit_margin = None
        
        if item.selling_price and item.landed_cost:
            profit_amount = item.selling_price - item.landed_cost
            profit_margin = profit_amount / item.landed_cost if item.landed_cost > 0 else 0
        
        profit_items.append(ProfitReportItem(
            item_id=item.id,
            item_name=item.name,
            category=item.category.value,
            purchase_price_usd=item.purchase_price_usd,
            landed_cost=item.landed_cost,
            selling_price=item.selling_price,
            profit_amount=profit_amount,
            profit_margin=profit_margin,
            sold=item.sold
        ))
    
    return profit_items


@router.get("/profit/containers", response_model=List[ContainerReport])
def get_container_reports(
    owner_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_manager_or_admin_user)
) -> Any:
    """Get profit reports by container."""
    query = db.query(Container)
    
    if owner_id:
        query = query.filter(Container.owner_id == owner_id)
    
    containers = query.all()
    reports = []
    
    for container in containers:
        # Calculate totals
        total_expenses = db.query(func.sum(ContainerExpense.amount_usd)).filter(
            ContainerExpense.container_id == container.id
        ).scalar() or 0
        
        items = db.query(Item).filter(Item.container_id == container.id).all()
        total_items = len(items)
        items_sold = len([i for i in items if i.sold])
        
        total_revenue = sum(i.selling_price or 0 for i in items if i.sold)
        total_cost = sum(i.landed_cost or 0 for i in items)
        total_profit = total_revenue - total_cost
        profit_margin = total_profit / total_cost if total_cost > 0 else 0
        
        reports.append(ContainerReport(
            container_id=container.id,
            container_name=container.name,
            total_expenses=total_expenses,
            total_items=total_items,
            items_sold=items_sold,
            total_revenue=total_revenue,
            total_profit=total_profit,
            profit_margin=profit_margin
        ))
    
    return reports


@router.get("/profit/categories", response_model=List[CategoryReport])
def get_category_reports(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get profit reports by category."""
    query = db.query(Item).join(Container)
    
    # Role-based filtering
    if current_user.role == UserRole.CLERK:
        query = query.filter(Container.owner_id == current_user.id)
    
    # Group by category
    category_data = {}
    items = query.all()
    
    for item in items:
        category = item.category.value
        if category not in category_data:
            category_data[category] = {
                'total_items': 0,
                'items_sold': 0,
                'total_investment': 0,
                'total_revenue': 0,
                'total_profit': 0
            }
        
        data = category_data[category]
        data['total_items'] += 1
        data['total_investment'] += item.landed_cost or 0
        
        if item.sold:
            data['items_sold'] += 1
            data['total_revenue'] += item.selling_price or 0
            data['total_profit'] += (item.selling_price or 0) - (item.landed_cost or 0)
    
    reports = []
    for category, data in category_data.items():
        average_margin = data['total_profit'] / data['total_investment'] if data['total_investment'] > 0 else 0
        
        reports.append(CategoryReport(
            category=category,
            total_items=data['total_items'],
            items_sold=data['items_sold'],
            total_investment=data['total_investment'],
            total_revenue=data['total_revenue'],
            total_profit=data['total_profit'],
            average_margin=average_margin
        ))
    
    return reports


