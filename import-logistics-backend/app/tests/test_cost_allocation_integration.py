# app/tests/test_cost_allocation_integration.py
"""Cost allocation against a REAL PostgreSQL database.

Skipped unless TEST_DATABASE_URL is set, e.g.
    TEST_DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/test
The tables are created before and dropped after the test session.
"""
import asyncio
import os
import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models import Base
from app.models.container import Container, ContainerType
from app.models.expense import ContainerExpense, ExpenseType
from app.models.item import Item, ItemCategory, ItemCondition
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.services.cost_allocation_service import AllocationError, CostAllocationService

URL = os.getenv("TEST_DATABASE_URL")
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL not set"),
]
D = Decimal


@pytest_asyncio.fixture
async def Session():
    engine = create_async_engine(URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


async def seed(Session, weights, prices, expense_total):
    async with Session() as db:
        org = Organization(name="T", slug=uuid.uuid4().hex[:12])
        db.add(org)
        await db.flush()
        user = User(
            tenant_id=org.id, email=f"{uuid.uuid4().hex[:8]}@x.com",
            username=uuid.uuid4().hex[:8], first_name="A", last_name="B",
            hashed_password="x", role=UserRole.ADMIN,
        )
        db.add(user)
        await db.flush()
        container = Container(
            tenant_id=org.id, owner_id=user.id, name="C", container_type=ContainerType.TWENTY_FT
        )
        db.add(container)
        await db.flush()
        for i, (w, p) in enumerate(zip(weights, prices)):
            db.add(Item(
                tenant_id=org.id, container_id=container.id, name=f"item{i}",
                category=ItemCategory.OTHER, condition=ItemCondition.NEW,
                purchase_price=p, purchase_currency="USD", fx_rate_to_usd=D("1"),
                purchase_price_usd=p, weight=w,
            ))
        db.add(ContainerExpense(
            tenant_id=org.id, container_id=container.id, expense_type=ExpenseType.SHIPPING_FEE,
            amount=expense_total, currency="USD", fx_rate_to_usd=D("1"), amount_usd=expense_total,
        ))
        await db.commit()
        return org.id, container.id


async def test_shares_add_up_exactly(Session):
    tenant, cid = await seed(Session, [D("1")] * 3, [D("10")] * 3, D("100.00"))
    async with Session() as db:
        result = await CostAllocationService(db).allocate_container_costs(cid, tenant, "weight_based")
    assert result["allocated_total"] == result["total_expenses"] == D("100.0000")
    assert sum(r["allocated_cost"] for r in result["items"]) == D("100.0000")


async def test_landed_cost_is_price_plus_share(Session):
    tenant, cid = await seed(Session, [D("1"), D("3")], [D("50"), D("70")], D("40.00"))
    async with Session() as db:
        result = await CostAllocationService(db).allocate_container_costs(cid, tenant, "weight_based")
    first, second = result["items"]
    assert first["allocated_cost"] == D("10.0000") and first["landed_cost"] == D("60.0000")
    assert second["allocated_cost"] == D("30.0000") and second["landed_cost"] == D("100.0000")


async def test_concurrent_allocations_leave_consistent_totals(Session):
    tenant, cid = await seed(Session, [D("1")] * 3, [D("10")] * 3, D("100.00"))

    async def run():
        async with Session() as db:
            return await CostAllocationService(db).allocate_container_costs(cid, tenant, "weight_based")

    await asyncio.gather(run(), run(), run())
    async with Session() as db:
        from sqlalchemy import func, select
        total = (await db.execute(select(func.sum(Item.allocated_cost)))).scalar_one()
    assert total == D("100.0000")


async def test_unknown_method_is_rejected(Session):
    tenant, cid = await seed(Session, [D("0.001")], [D("10")], D("5.00"))
    async with Session() as db:
        with pytest.raises(AllocationError):
            await CostAllocationService(db).allocate_container_costs(cid, tenant, "nonsense")


async def test_other_tenant_cannot_allocate(Session):
    tenant, cid = await seed(Session, [D("1")], [D("10")], D("5.00"))
    async with Session() as db:
        assert await CostAllocationService(db).allocate_container_costs(cid, tenant + 999) is None
