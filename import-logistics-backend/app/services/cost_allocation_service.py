# app/services/cost_allocation_service.py
import logging
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import transaction
from app.models.container import AllocationMethod, Container
from app.models.expense import ContainerExpense
from app.models.item import Item
from app.utils.money import MONEY_PLACES, ZERO, allocate_proportionally, quantize, to_decimal

logger = logging.getLogger(__name__)


class AllocationError(Exception):
    """A business rule prevents allocation (maps to HTTP 422)."""


class CostAllocationService:
    """Spreads a container's shared expenses over its items.

    * All maths is Decimal; the parts always add up to the expense total
      exactly (largest-remainder rounding).
    * The container row is locked (SELECT ... FOR UPDATE) so two concurrent
      allocation requests cannot interleave.
    * Everything runs in one transaction: all items are updated or none.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def allocate_container_costs(
        self,
        container_id: int,
        tenant_id: int,
        method: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        async with transaction(self.db):
            container = (
                await self.db.execute(
                    select(Container)
                    .where(
                        Container.id == container_id,
                        Container.tenant_id == tenant_id,
                        Container.deleted_at.is_(None),
                    )
                    .with_for_update()
                )
            ).scalar_one_or_none()
            if container is None:
                return None

            chosen = method or container.allocation_method.value
            valid = {m.value for m in AllocationMethod}
            if chosen not in valid:
                raise AllocationError(
                    f"Unknown allocation method {chosen!r}; use one of {sorted(valid)}"
                )

            items = list(
                (
                    await self.db.execute(
                        select(Item)
                        .where(
                            Item.container_id == container_id,
                            Item.tenant_id == tenant_id,
                            Item.deleted_at.is_(None),
                        )
                        .order_by(Item.id)
                    )
                ).scalars().all()
            )
            if not items:
                raise AllocationError("Container has no items to allocate costs to")

            total_expenses = quantize(
                (
                    await self.db.execute(
                        select(func.coalesce(func.sum(ContainerExpense.amount_usd), 0)).where(
                            ContainerExpense.container_id == container_id,
                            ContainerExpense.tenant_id == tenant_id,
                        )
                    )
                ).scalar_one()
            )

            by_weight = chosen == AllocationMethod.WEIGHT_BASED.value
            bases = [
                to_decimal(i.weight if by_weight else i.purchase_price_usd) for i in items
            ]
            basis_total = sum(bases, ZERO)
            if basis_total == 0:
                raise AllocationError(
                    "Total item weight is zero" if by_weight else "Total item value is zero"
                )

            shares = allocate_proportionally(total_expenses, bases, MONEY_PLACES)

            rows = []
            for item, base, share in zip(items, bases, shares):
                item.allocated_cost = share
                item.landed_cost = quantize(to_decimal(item.purchase_price_usd) + share)
                rows.append(
                    {
                        "item_id": item.id,
                        "item_name": item.name,
                        "ratio": quantize(base / basis_total, 6),
                        "allocated_cost": share,
                        "landed_cost": item.landed_cost,
                    }
                )

            allocated_total = sum(shares, ZERO)
            if allocated_total != total_expenses:  # cannot happen; protects the books
                raise RuntimeError("allocation does not add up to the expense total")

        logger.info(
            "Cost allocated (%s): container=%d items=%d total=%s",
            chosen, container_id, len(items), total_expenses,
        )
        return {
            "method": chosen,
            "total_expenses": total_expenses,
            "allocated_total": allocated_total,
            "basis_total": basis_total,
            "items": rows,
        }
