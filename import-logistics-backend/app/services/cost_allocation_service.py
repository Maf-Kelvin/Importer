# app/services/cost_allocation_service.py
import logging
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import transaction
from app.models.container import AllocationMethod, Container
from app.models.expense import ContainerExpense
from app.models.item import Item

logger = logging.getLogger(__name__)


class CostAllocationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def allocate_container_costs(
        self,
        container_id: int,
        method: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        # Load container
        result = await self.db.execute(
            select(Container).where(Container.id == container_id)
        )
        container = result.scalar_one_or_none()
        if not container:
            return None

        # Resolve method
        allocation_method = method or container.allocation_method.value

        # Load items
        items_result = await self.db.execute(
            select(Item).where(
                Item.container_id == container_id,
                Item.deleted_at.is_(None),
            )
        )
        items = list(items_result.scalars().all())
        if not items:
            return {"message": "No items in container to allocate costs to"}

        # Total expenses — fixed: uses sqlalchemy func, not self.db.func
        expense_result = await self.db.execute(
            select(func.sum(ContainerExpense.amount_usd)).where(
                ContainerExpense.container_id == container_id
            )
        )
        total_expenses: float = expense_result.scalar_one() or 0.0

        if allocation_method == AllocationMethod.WEIGHT_BASED.value:
            return await self._allocate_by_weight(items, total_expenses)
        return await self._allocate_by_value(items, total_expenses)

    async def _allocate_by_weight(
        self, items: list[Item], total_expenses: float
    ) -> dict[str, Any]:
        total_weight = sum(i.weight for i in items)
        if total_weight == 0:
            return {"error": "Total weight is zero — cannot allocate by weight"}

        allocated = []
        async with transaction(self.db):
            for item in items:
                ratio          = item.weight / total_weight
                alloc_cost     = total_expenses * ratio
                item.allocated_cost = alloc_cost
                item.landed_cost    = item.purchase_price_usd + alloc_cost
                allocated.append({
                    "item_id":        item.id,
                    "item_name":      item.name,
                    "weight_ratio":   round(ratio, 6),
                    "allocated_cost": round(alloc_cost, 4),
                    "landed_cost":    round(item.landed_cost, 4),
                })

        logger.info(
            "Cost allocated (weight) for %d items, total_expenses=%.2f",
            len(items), total_expenses,
        )
        return {
            "method":         "weight_based",
            "total_expenses": total_expenses,
            "total_weight":   total_weight,
            "items":          allocated,
        }

    async def _allocate_by_value(
        self, items: list[Item], total_expenses: float
    ) -> dict[str, Any]:
        total_value = sum(i.purchase_price_usd for i in items)
        if total_value == 0:
            return {"error": "Total value is zero — cannot allocate by value"}

        allocated = []
        async with transaction(self.db):
            for item in items:
                ratio          = item.purchase_price_usd / total_value
                alloc_cost     = total_expenses * ratio
                item.allocated_cost = alloc_cost
                item.landed_cost    = item.purchase_price_usd + alloc_cost
                allocated.append({
                    "item_id":        item.id,
                    "item_name":      item.name,
                    "value_ratio":    round(ratio, 6),
                    "allocated_cost": round(alloc_cost, 4),
                    "landed_cost":    round(item.landed_cost, 4),
                })

        logger.info(
            "Cost allocated (value) for %d items, total_expenses=%.2f",
            len(items), total_expenses,
        )
        return {
            "method":       "value_based",
            "total_expenses": total_expenses,
            "total_value":  total_value,
            "items":        allocated,
        }