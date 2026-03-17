# app/services/container_service.py
import logging
from datetime import date, datetime, UTC
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import transaction
from app.models.container import AllocationMethod, Container
from app.models.expense import ContainerExpense
from app.models.item import Item
from app.models.user import User, UserRole
from app.schemas.common import PagedResponse, PaginationParams
from app.schemas.container import ContainerCreate, ContainerUpdate
from app.schemas.expense import ExpenseCreate, ExpenseUpdate
from app.schemas.item import ItemCreate, ItemUpdate, MarkSoldRequest
from app.services.fx_service import FXService

logger = logging.getLogger(__name__)


class ContainerService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.fx  = FXService()

    # ==================================================================
    # Containers
    # ==================================================================

    async def create_container(
        self, data: ContainerCreate, owner: User
    ) -> Container:
        async with transaction(self.db):
            container = Container(
                tenant_id=owner.tenant_id,
                owner_id=owner.id,
                name=data.name,
                container_type=data.container_type,
                msc_container_number=data.msc_container_number,
                allocation_method=data.allocation_method,
                notes=data.notes,
            )
            self.db.add(container)
        await self.db.refresh(container)
        logger.info("Container created: id=%d owner=%d", container.id, owner.id)
        return container

    async def get_containers(
        self,
        params: PaginationParams,
        current_user: User,
        owner_id: Optional[int] = None,
        container_type: Optional[str] = None,
        is_shipped: Optional[bool] = None,
    ) -> PagedResponse[Container]:
        q = (
            select(Container)
            .where(
                Container.tenant_id == current_user.tenant_id,
                Container.deleted_at.is_(None),
            )
        )

        # Clerks only see their own containers
        if current_user.role == UserRole.CLERK:
            q = q.where(Container.owner_id == current_user.id)
        elif owner_id:
            q = q.where(Container.owner_id == owner_id)

        if container_type:
            q = q.where(Container.container_type == container_type)
        if is_shipped is not None:
            q = q.where(Container.is_shipped == is_shipped)

        # Count + fetch in two async calls — avoids N+1
        total_result = await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )
        total = total_result.scalar_one()

        items_result = await self.db.execute(
            q.options(selectinload(Container.owner))
             .offset(params.offset)
             .limit(params.limit)
        )
        containers = items_result.scalars().all()

        return PagedResponse.create(list(containers), total, params)

    async def get_container_by_id(
        self, container_id: int, current_user: User
    ) -> Optional[Container]:
        q = (
            select(Container)
            .where(
                Container.id == container_id,
                Container.tenant_id == current_user.tenant_id,
                Container.deleted_at.is_(None),
            )
            .options(
                selectinload(Container.items),
                selectinload(Container.expenses),
            )
        )
        if current_user.role == UserRole.CLERK:
            q = q.where(Container.owner_id == current_user.id)

        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def update_container(
        self,
        container_id: int,
        data: ContainerUpdate,
        current_user: User,
    ) -> Optional[Container]:
        container = await self.get_container_by_id(container_id, current_user)
        if not container:
            return None

        async with transaction(self.db):
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(container, field, value)

        await self.db.refresh(container)
        return container

    async def seal_container(
        self, container_id: int, current_user: User
    ) -> Optional[Container]:
        container = await self.get_container_by_id(container_id, current_user)
        if not container:
            return None
        async with transaction(self.db):
            container.is_sealed = True
        await self.db.refresh(container)
        return container

    async def delete_container(
        self, container_id: int, current_user: User
    ) -> bool:
        container = await self.get_container_by_id(container_id, current_user)
        if not container:
            return False
        async with transaction(self.db):
            container.soft_delete()
        logger.info("Container soft-deleted: id=%d by user=%d", container_id, current_user.id)
        return True

    # ==================================================================
    # Expenses
    # ==================================================================

    async def create_expense(
        self, data: ExpenseCreate, current_user: User
    ) -> Optional[ContainerExpense]:
        container = await self.get_container_by_id(data.container_id, current_user)
        if not container:
            return None

        fx_rate   = await self.fx.get_fx_rate(data.currency, "USD")
        amount_usd = data.amount * fx_rate

        async with transaction(self.db):
            expense = ContainerExpense(
                tenant_id=current_user.tenant_id,
                container_id=data.container_id,
                expense_type=data.expense_type,
                amount=data.amount,
                currency=data.currency,
                description=data.description,
                fx_rate_to_usd=fx_rate,
                amount_usd=amount_usd,
            )
            self.db.add(expense)

        await self.db.refresh(expense)
        return expense

    async def get_container_expenses(
        self, container_id: int, current_user: User
    ) -> list[ContainerExpense]:
        container = await self.get_container_by_id(container_id, current_user)
        if not container:
            return []
        result = await self.db.execute(
            select(ContainerExpense).where(
                ContainerExpense.container_id == container_id,
                ContainerExpense.tenant_id == current_user.tenant_id,
            )
        )
        return list(result.scalars().all())

    async def update_expense(
        self,
        expense_id: int,
        data: ExpenseUpdate,
        current_user: User,
    ) -> Optional[ContainerExpense]:
        result = await self.db.execute(
            select(ContainerExpense).where(
                ContainerExpense.id == expense_id,
                ContainerExpense.tenant_id == current_user.tenant_id,
            )
        )
        expense = result.scalar_one_or_none()
        if not expense:
            return None

        async with transaction(self.db):
            update_data = data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(expense, field, value)
            # Recalculate USD amount if currency or amount changed
            if "amount" in update_data or "currency" in update_data:
                fx_rate = await self.fx.get_fx_rate(expense.currency, "USD")
                expense.fx_rate_to_usd = fx_rate
                expense.amount_usd = expense.amount * fx_rate

        await self.db.refresh(expense)
        return expense

    async def delete_expense(
        self, expense_id: int, current_user: User
    ) -> bool:
        result = await self.db.execute(
            select(ContainerExpense).where(
                ContainerExpense.id == expense_id,
                ContainerExpense.tenant_id == current_user.tenant_id,
            )
        )
        expense = result.scalar_one_or_none()
        if not expense:
            return False
        async with transaction(self.db):
            await self.db.delete(expense)
        return True

    # ==================================================================
    # Items
    # ==================================================================

    async def create_item(
        self, data: ItemCreate, current_user: User
    ) -> Optional[Item]:
        container = await self.get_container_by_id(data.container_id, current_user)
        if not container or container.is_sealed:
            return None

        fx_rate            = await self.fx.get_fx_rate(data.purchase_currency, "USD")
        purchase_price_usd = data.purchase_price * fx_rate

        async with transaction(self.db):
            item = Item(
                tenant_id=current_user.tenant_id,
                container_id=data.container_id,
                name=data.name,
                description=data.description,
                category=data.category,
                condition=data.condition,
                purchase_price=data.purchase_price,
                purchase_currency=data.purchase_currency,
                purchase_date=data.purchase_date,
                fx_rate_to_usd=fx_rate,
                purchase_price_usd=purchase_price_usd,
                weight=data.weight,
                volume=data.volume,
            )
            self.db.add(item)

        await self.db.refresh(item)
        logger.info("Item created: id=%d container=%d", item.id, item.container_id)
        return item

    async def get_items(
        self,
        params: PaginationParams,
        current_user: User,
        container_id: Optional[int] = None,
        category: Optional[str] = None,
        condition: Optional[str] = None,
        sold: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> PagedResponse[Item]:
        q = select(Item).where(
            Item.tenant_id == current_user.tenant_id,
            Item.deleted_at.is_(None),
        )

        if current_user.role == UserRole.CLERK:
            q = q.join(Container).where(Container.owner_id == current_user.id)

        if container_id:
            q = q.where(Item.container_id == container_id)
        if category:
            q = q.where(Item.category == category)
        if condition:
            q = q.where(Item.condition == condition)
        if sold is not None:
            q = q.where(Item.sold == sold)
        if search:
            q = q.where(Item.name.ilike(f"%{search}%"))

        total_result = await self.db.execute(
            select(func.count()).select_from(q.subquery())
        )
        total = total_result.scalar_one()

        items_result = await self.db.execute(
            q.offset(params.offset).limit(params.limit)
        )
        items = list(items_result.scalars().all())

        return PagedResponse.create(items, total, params)

    async def get_item_by_id(
        self, item_id: int, current_user: User
    ) -> Optional[Item]:
        q = (
            select(Item)
            .where(
                Item.id == item_id,
                Item.tenant_id == current_user.tenant_id,
                Item.deleted_at.is_(None),
            )
            .options(selectinload(Item.price_records))
        )
        if current_user.role == UserRole.CLERK:
            q = q.join(Container).where(Container.owner_id == current_user.id)

        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def update_item(
        self,
        item_id: int,
        data: ItemUpdate,
        current_user: User,
    ) -> Optional[Item]:
        item = await self.get_item_by_id(item_id, current_user)
        if not item:
            return None

        async with transaction(self.db):
            update_data = data.model_dump(exclude_unset=True)
            # Recalculate USD price if purchase price or currency changed
            if "purchase_price" in update_data or "purchase_currency" in update_data:
                currency = update_data.get("purchase_currency", item.purchase_currency)
                price    = update_data.get("purchase_price",    item.purchase_price)
                fx_rate  = await self.fx.get_fx_rate(currency, "USD")
                item.fx_rate_to_usd     = fx_rate
                item.purchase_price_usd = price * fx_rate
            for field, value in update_data.items():
                setattr(item, field, value)

        await self.db.refresh(item)
        return item

    async def delete_item(
        self, item_id: int, current_user: User
    ) -> bool:
        item = await self.get_item_by_id(item_id, current_user)
        if not item:
            return False
        async with transaction(self.db):
            item.soft_delete()
        return True

    async def mark_item_sold(
        self,
        item_id: int,
        data: MarkSoldRequest,
        current_user: User,
    ) -> Optional[Item]:
        from app.models.commerce import Sale

        item = await self.get_item_by_id(item_id, current_user)
        if not item or item.sold:
            return None

        async with transaction(self.db):
            sold_at = datetime.combine(
                data.sold_date or date.today(), datetime.min.time()
            ).replace(tzinfo=UTC)

            item.sold          = True
            item.selling_price = data.selling_price
            item.sold_date     = data.sold_date or date.today()

            # Create dedicated Sale record
            sale = Sale(
                tenant_id=current_user.tenant_id,
                item_id=item.id,
                customer_id=data.customer_id,
                sold_by=current_user.id,
                sale_price=data.selling_price,
                currency="USD",
                sold_at=sold_at,
                notes=data.notes,
            )
            self.db.add(sale)

        await self.db.refresh(item)
        logger.info(
            "Item sold: id=%d price=%.2f by user=%d",
            item.id, data.selling_price, current_user.id,
        )
        return item

    # ==================================================================
    # Cost allocation
    # ==================================================================

    async def allocate_costs(
        self,
        container_id: int,
        allocation_method: Optional[str],
        current_user: User,
    ) -> Optional[dict[str, Any]]:
        from app.services.cost_allocation_service import CostAllocationService
        container = await self.get_container_by_id(container_id, current_user)
        if not container:
            return None
        svc = CostAllocationService(self.db)
        return await svc.allocate_container_costs(container_id, allocation_method)