# scripts/init_db.py
"""Initialize database with tables and first superuser."""

import asyncio
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.core.config import settings
from app.models import Base
from app.models.user import User, UserRole
from app.core.security import get_password_hash


def create_tables():
    """Create all database tables."""
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully!")


def create_first_superuser(db: Session):
    """Create the first superuser."""
    print("Creating first superuser...")
    
    # Check if superuser already exists
    existing_user = db.query(User).filter(User.email == settings.FIRST_SUPERUSER).first()
    if existing_user:
        print(f"⚠️  Superuser {settings.FIRST_SUPERUSER} already exists!")
        return
    
    # Create superuser
    superuser = User(
        email=settings.FIRST_SUPERUSER,
        username="admin",
        first_name="Super",
        last_name="Admin",
        hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
        role=UserRole.ADMIN,
        is_active=True,
        is_superuser=True
    )
    
    db.add(superuser)
    db.commit()
    
    print(f"✅ Superuser {settings.FIRST_SUPERUSER} created successfully!")
    print(f"   Username: admin")
    print(f"   Password: {settings.FIRST_SUPERUSER_PASSWORD}")


def main():
    """Main initialization function."""
    print("🚀 Initializing Import Logistics Database...")
    
    # Create tables
    create_tables()
    
    # Create first superuser
    db = SessionLocal()
    try:
        create_first_superuser(db)
    finally:
        db.close()
    
    print("🎉 Database initialization completed!")


if __name__ == "__main__":
    main()
