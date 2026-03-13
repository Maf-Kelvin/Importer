# app/routers/expenses.py
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.routers.deps import get_db, get_current_active_user, get_clerk_or_higher_user
from app.models.user import User
from app.schemas.expense import ExpenseCreate, ExpenseUpdate, ExpenseInDB
from app.services.container_service import ContainerService

router = APIRouter()


@router.post("/", response_model=ExpenseInDB)
def create_expense(
    expense_create: ExpenseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Create container expense."""
    container_service = ContainerService(db)
    return container_service.create_expense(expense_create, current_user)


@router.get("/container/{container_id}", response_model=List[ExpenseInDB])
def get_container_expenses(
    container_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get all expenses for a container."""
    container_service = ContainerService(db)
    return container_service.get_container_expenses(container_id, current_user)


@router.put("/{expense_id}", response_model=ExpenseInDB)
def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Update expense."""
    container_service = ContainerService(db)
    expense = container_service.update_expense(expense_id, expense_update, current_user)
    
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    return expense


@router.delete("/{expense_id}")
def delete_expense(
    expense_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_clerk_or_higher_user)
) -> Any:
    """Delete expense."""
    container_service = ContainerService(db)
    success = container_service.delete_expense(expense_id, current_user)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found"
        )
    
    return {"message": "Expense deleted successfully"}

