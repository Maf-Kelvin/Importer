# app/routers/customers.py
"""Customers of one organisation. Every query is tenant-scoped; a customer id
from another organisation behaves as if it does not exist (404)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.database import transaction
from app.models.commerce import Customer
from app.routers.deps import ClerkUser, CurrentUser, DBDep, ManagerUser
from app.schemas.common import PagedResponse, PaginationParams
from app.schemas.customer import CustomerCreate, CustomerInDB, CustomerUpdate
from app.services.audit_service import AuditService
from app.utils.audit import diff, snapshot

router = APIRouter()
FIELDS = ("name", "email", "phone", "address", "notes")


async def _get(db, customer_id: int, tenant_id: int) -> Optional[Customer]:
    return (
        await db.execute(
            select(Customer).where(
                Customer.id == customer_id,
                Customer.tenant_id == tenant_id,
                Customer.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()


@router.post("/", response_model=CustomerInDB, status_code=status.HTTP_201_CREATED,
             summary="Create a customer")
async def create_customer(data: CustomerCreate, db: DBDep, current_user: ClerkUser):
    customer = Customer(tenant_id=current_user.tenant_id, **data.model_dump())
    async with transaction(db):
        db.add(customer)
        await db.flush()
        AuditService(db).add(
            tenant_id=current_user.tenant_id, user_id=current_user.id, action="customer.created",
            entity_type="Customer", entity_id=customer.id, changes=snapshot(customer, FIELDS),
        )
    await db.refresh(customer)
    return customer


@router.get("/", response_model=PagedResponse[CustomerInDB], summary="List customers")
async def list_customers(
    db: DBDep,
    current_user: CurrentUser,
    params: PaginationParams = Depends(),
    search: Optional[str] = Query(None, description="Match on name or email"),
):
    conditions = [Customer.tenant_id == current_user.tenant_id, Customer.deleted_at.is_(None)]
    if search:
        like = f"%{search}%"
        conditions.append(Customer.name.ilike(like) | Customer.email.ilike(like))
    total = (await db.execute(select(func.count(Customer.id)).where(*conditions))).scalar_one()
    rows = (
        await db.execute(
            select(Customer).where(*conditions).order_by(Customer.name)
            .offset(params.offset).limit(params.limit)
        )
    ).scalars().all()
    return PagedResponse.create(list(rows), total, params)


@router.get("/{customer_id}", response_model=CustomerInDB, summary="Get a customer")
async def get_customer(customer_id: int, db: DBDep, current_user: CurrentUser):
    customer = await _get(db, customer_id, current_user.tenant_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    return customer


@router.put("/{customer_id}", response_model=CustomerInDB, summary="Update a customer")
async def update_customer(customer_id: int, data: CustomerUpdate, db: DBDep, current_user: ClerkUser):
    customer = await _get(db, customer_id, current_user.tenant_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    before = snapshot(customer, FIELDS)
    async with transaction(db):
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(customer, field, value)
        AuditService(db).add(
            tenant_id=current_user.tenant_id, user_id=current_user.id, action="customer.updated",
            entity_type="Customer", entity_id=customer.id,
            changes=diff(before, snapshot(customer, FIELDS)),
        )
    await db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete a customer (manager+; sales history is kept)")
async def delete_customer(customer_id: int, db: DBDep, current_user: ManagerUser):
    customer = await _get(db, customer_id, current_user.tenant_id)
    if not customer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")
    async with transaction(db):
        customer.soft_delete()
        AuditService(db).add(
            tenant_id=current_user.tenant_id, user_id=current_user.id, action="customer.deleted",
            entity_type="Customer", entity_id=customer.id, changes=snapshot(customer, FIELDS),
        )
    return None
