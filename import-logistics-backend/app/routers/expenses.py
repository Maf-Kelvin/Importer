# app/routers/expenses.py
from fastapi import APIRouter, HTTPException, status

from app.routers.deps import ClerkUser, CurrentUser, DBDep
from app.schemas.expense import ExpenseCreate, ExpenseInDB, ExpenseUpdate
from app.services.container_service import ContainerService

router = APIRouter()


@router.post(
    "/",
    response_model=ExpenseInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Add expense to a container",
)
async def create_expense(data: ExpenseCreate, db: DBDep, current_user: ClerkUser):
    svc     = ContainerService(db)
    expense = await svc.create_expense(data, current_user)
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found or access denied",
        )
    return expense


@router.get(
    "/container/{container_id}",
    response_model=list[ExpenseInDB],
    summary="List all expenses for a container",
)
async def list_container_expenses(
    container_id: int, db: DBDep, current_user: CurrentUser
):
    svc = ContainerService(db)
    return await svc.get_container_expenses(container_id, current_user)


@router.put(
    "/{expense_id}",
    response_model=ExpenseInDB,
    summary="Update an expense",
)
async def update_expense(
    expense_id: int, data: ExpenseUpdate, db: DBDep, current_user: ClerkUser
):
    svc     = ContainerService(db)
    expense = await svc.update_expense(expense_id, data, current_user)
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense


@router.delete("/{expense_id}", summary="Delete an expense")
async def delete_expense(expense_id: int, db: DBDep, current_user: ClerkUser):
    svc     = ContainerService(db)
    deleted = await svc.delete_expense(expense_id, current_user)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return {"message": "Expense deleted"}