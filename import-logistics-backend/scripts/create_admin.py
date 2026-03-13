# scripts/create_admin.py
"""Create additional admin users."""

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash
import sys


def create_admin_user(email: str, username: str, password: str, first_name: str, last_name: str):
    """Create a new admin user."""
    db = SessionLocal()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            print(f"❌ User with email {email} or username {username} already exists!")
            return False
        
        # Create admin user
        admin_user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            hashed_password=get_password_hash(password),
            role=UserRole.ADMIN,
            is_active=True,
            is_superuser=False
        )
        
        db.add(admin_user)
        db.commit()
        
        print(f"✅ Admin user {email} created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 6:
        print("Usage: python create_admin.py <email> <username> <password> <first_name> <last_name>")
        sys.exit(1)
    
    email, username, password, first_name, last_name = sys.argv[1:6]
    create_admin_user(email, username, password, first_name, last_name)