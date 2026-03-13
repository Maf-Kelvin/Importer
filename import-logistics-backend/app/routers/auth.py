# app/routers/auth.py
from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.routers.deps import get_db
from app.core import security
from app.core.config import settings
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserInDB
from app.services.auth_service import AuthService

router = APIRouter()


@router.post("/login", response_model=Token)
def login_for_access_token(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """OAuth2 compatible token login."""
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        subject=user.username, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user
    }


@router.post("/register", response_model=UserInDB)
def register(
    user_create: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """Create new user."""
    auth_service = AuthService(db)
    
    # Check if user exists
    if auth_service.get_user_by_email(user_create.email):
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists."
        )
    
    if auth_service.get_user_by_username(user_create.username):
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists."
        )
    
    user = auth_service.create_user(user_create)
    return user