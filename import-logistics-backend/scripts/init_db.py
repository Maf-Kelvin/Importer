# scripts/init_db.py
"""Bootstrap the first organisation (tenant) and superuser.

This script does NOT create tables. Run `alembic upgrade head` first.

Required environment variables:
    FIRST_SUPERUSER_EMAIL, FIRST_SUPERUSER_USERNAME, FIRST_SUPERUSER_PASSWORD
"""
import sys

from sqlalchemy import inspect, select

from app.core.config import settings
from app.core.database import SyncSessionLocal, sync_engine
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User, UserRole

DEFAULT_ORG_SLUG = "default"


def main() -> int:
    email = settings.FIRST_SUPERUSER_EMAIL
    username = settings.FIRST_SUPERUSER_USERNAME
    password = settings.FIRST_SUPERUSER_PASSWORD
    if not (email and username and password):
        print("Set FIRST_SUPERUSER_EMAIL, FIRST_SUPERUSER_USERNAME and FIRST_SUPERUSER_PASSWORD.")
        return 1
    if settings.ENVIRONMENT == "production" and len(password) < 12:
        print("In production the superuser password must be at least 12 characters.")
        return 1
    if not inspect(sync_engine).has_table("organizations"):
        print("Tables not found. Run `alembic upgrade head` first.")
        return 1

    with SyncSessionLocal() as db:
        org = db.execute(
            select(Organization).where(Organization.slug == DEFAULT_ORG_SLUG)
        ).scalar_one_or_none()
        if org is None:
            org = Organization(name="Default Organization", slug=DEFAULT_ORG_SLUG)
            db.add(org)
            db.flush()

        exists = db.execute(
            select(User).where((User.email == email) | (User.username == username))
        ).scalar_one_or_none()
        if exists:
            print("Superuser already exists - nothing to do.")
            return 0

        db.add(
            User(
                tenant_id=org.id,
                email=email,
                username=username,
                first_name="Super",
                last_name="Admin",
                hashed_password=get_password_hash(password),
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=True,
            )
        )
        db.commit()
    print(f"Created organisation '{DEFAULT_ORG_SLUG}' and superuser '{username}'.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
