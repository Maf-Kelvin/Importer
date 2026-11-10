# scripts/create_admin.py
"""Create an additional admin user inside an existing organisation.

Usage:
    python -m scripts.create_admin EMAIL USERNAME PASSWORD FIRST LAST [ORG_SLUG]
"""
import sys

from sqlalchemy import select

from app.core.database import SyncSessionLocal
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User, UserRole


def create_admin_user(
    email: str, username: str, password: str,
    first_name: str, last_name: str, org_slug: str = "default",
) -> bool:
    with SyncSessionLocal() as db:
        org = db.execute(
            select(Organization).where(Organization.slug == org_slug)
        ).scalar_one_or_none()
        if org is None:
            print(f"Organisation '{org_slug}' not found. Run scripts/init_db.py first.")
            return False
        exists = db.execute(
            select(User).where((User.email == email) | (User.username == username))
        ).scalar_one_or_none()
        if exists:
            print("A user with that email or username already exists.")
            return False
        db.add(
            User(
                tenant_id=org.id, email=email, username=username,
                first_name=first_name, last_name=last_name,
                hashed_password=get_password_hash(password),
                role=UserRole.ADMIN, is_active=True, is_superuser=False,
            )
        )
        db.commit()
    print(f"Admin user {username} created in '{org_slug}'.")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 6:
        print(__doc__)
        sys.exit(1)
    ok = create_admin_user(*sys.argv[1:7])
    sys.exit(0 if ok else 1)
