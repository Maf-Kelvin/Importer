# app/api/v1/users.py
from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_active_user, get_admin_user
from app.models.user import User
from app.schemas.user import UserInDB, UserCreate, UserUpdate
from app.schemas.common import PaginatedResponse
from app.services.auth_service import AuthService

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[UserInDB])
def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> Any:
    """Get all users (admin only)."""
    total = db.query(User).count()
    users = db.query(User).offset(skip).limit(limit).all()
    
    return {
        'items': users,
        'total': total,
        'page': (skip // limit) + 1,
        'per_page': limit,
        'pages': (total + limit - 1) // limit
    }


@router.get("/me", response_model=UserInDB)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get current user information."""
    return current_user


@router.put("/me", response_model=UserInDB)
def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Update current user."""
    auth_service = AuthService(db)
    
    # Users can only update their own basic info (not role/permissions)
    allowed_updates = user_update.dict(exclude={'role', 'is_active'}, exclude_unset=True)
    
    for field, value in allowed_updates.items():
        if field == 'password' and value:
            from app.core.security import get_password_hash
            setattr(current_user, 'hashed_password', get_password_hash(value))
        elif field != 'password':
            setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/", response_model=UserInDB)
def create_user(
    user_create: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> Any:
    """Create new user (admin only)."""
    auth_service = AuthService(db)
    
    if auth_service.get_user_by_email(user_create.email):
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )
    
    if auth_service.get_user_by_username(user_create.username):
        raise HTTPException(
            status_code=400,
            detail="User with this username already exists"
        )
    
    return auth_service.create_user(user_create)


@router.put("/{user_id}", response_model=UserInDB)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
) -> Any:
    """Update user (admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == 'password' and value:
            from app.core.security import get_password_hash
            setattr(user, 'hashed_password', get_password_hash(value))
        elif field != 'password':
            setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user
