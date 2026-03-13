# app/services/auth_service.py
from typing import Optional
from sqlalchemy.orm import Session
from app.core.security import verify_password, get_password_hash
from app.models.user import User
from app.schemas.user import UserCreate


class AuthService:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.db.query(User).filter(User.email == email).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return self.db.query(User).filter(User.username == username).first()
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/password."""
        user = self.get_user_by_username(username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
    
    def create_user(self, user_create: UserCreate) -> User:
        """Create new user."""
        hashed_password = get_password_hash(user_create.password)
        
        user = User(
            email=user_create.email,
            username=user_create.username,
            first_name=user_create.first_name,
            last_name=user_create.last_name,
            role=user_create.role,
            hashed_password=hashed_password,
            is_active=user_create.is_active
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
