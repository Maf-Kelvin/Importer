# app/services/cost_allocation_service.py
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models.container import Container, AllocationMethod
from app.models.item import Item
from app.models.expense import ContainerExpense


class CostAllocationService:
    def __init__(self, db: Session):
        self.db = db
    
    def allocate_container_costs(self, container_id: int, method: str = None) -> Dict:
        """Allocate container costs to items based on specified method."""
        container = self.db.query(Container).filter(Container.id == container_id).first()
        if not container:
            return None
        
        # Determine allocation method
        allocation_method = method or container.allocation_method.value
        
        # Get all items in container
        items = self.db.query(Item).filter(Item.container_id == container_id).all()
        if not items:
            return {"message": "No items in container to allocate costs to"}
        
        # Get total expenses
        total_expenses_usd = self.db.query(
            self.db.func.sum(ContainerExpense.amount_usd)
        ).filter(ContainerExpense.container_id == container_id).scalar() or 0
        
        if allocation_method == AllocationMethod.WEIGHT_BASED.value:
            return self._allocate_by_weight(items, total_expenses_usd)
        else:
            return self._allocate_by_value(items, total_expenses_usd)
    
    def _allocate_by_weight(self, items: List[Item], total_expenses: float) -> Dict:
        """Allocate costs based on weight."""
        total_weight = sum(item.weight for item in items)
        
        if total_weight == 0:
            return {"error": "Total weight is zero, cannot allocate by weight"}
        
        allocated_items = []
        for item in items:
            weight_ratio = item.weight / total_weight
            allocated_cost = total_expenses * weight_ratio
            
            item.allocated_cost = allocated_cost
            item.landed_cost = item.purchase_price_usd + allocated_cost
            
            allocated_items.append({
                "item_id": item.id,
                "weight_ratio": weight_ratio,
                "allocated_cost": allocated_cost,
                "landed_cost": item.landed_cost
            })
        
        self.db.commit()
        
        return {
            "method": "weight_based",
            "total_expenses": total_expenses,
            "total_weight": total_weight,
            "items": allocated_items
        }
    
    def _allocate_by_value(self, items: List[Item], total_expenses: float) -> Dict:
        """Allocate costs based on purchase value."""
        total_value = sum(item.purchase_price_usd for item in items)
        
        if total_value == 0:
            return {"error": "Total value is zero, cannot allocate by value"}
        
        allocated_items = []
        for item in items:
            value_ratio = item.purchase_price_usd / total_value
            allocated_cost = total_expenses * value_ratio
            
            item.allocated_cost = allocated_cost
            item.landed_cost = item.purchase_price_usd + allocated_cost
            
            allocated_items.append({
                "item_id": item.id,
                "value_ratio": value_ratio,
                "allocated_cost": allocated_cost,
                "landed_cost": item.landed_cost
            })
        
        self.db.commit()
        
        return {
            "method": "value_based",
            "total_expenses": total_expenses,
            "total_value": total_value,
            "items": allocated_items
        }