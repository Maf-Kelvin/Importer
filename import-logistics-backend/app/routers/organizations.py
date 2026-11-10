# app/routers/organizations.py
"""Tenant (organisation) onboarding.

Creating an organisation is a platform-administrator action (superuser only):
it creates the organisation and its first admin user atomically.
Public sign-up is intentionally not offered.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import transaction
from app.core.security import get_password_hash
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.routers.deps import CurrentUser, DBDep, SuperUser
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService

router = APIRouter()


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,98}[a-z0-9]$",
                      description="Lowercase letters, digits and hyphens")
    admin_email: EmailStr
    admin_username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    admin_password: str = Field(min_length=12, max_length=128)
    admin_first_name: str = Field(min_length=1, max_length=100)
    admin_last_name: str = Field(min_length=1, max_length=100)


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    plan: str
    is_active: bool
    max_users: int
    max_containers: int


class OrganizationCreated(OrganizationOut):
    admin_user_id: int


@router.post(
    "/",
    response_model=OrganizationCreated,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organisation and its first admin (platform administrator only)",
)
async def create_organization(
    body: OrganizationCreate, db: DBDep, current_user: SuperUser
):
    auth = AuthService(db)
    taken = (
        await db.execute(select(Organization.id).where(Organization.slug == body.slug))
    ).first()
    if taken:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Organisation slug already in use")
    if await auth.get_user_by_email(body.admin_email):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Admin email already registered")
    if await auth.get_user_by_username(body.admin_username):
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Admin username already taken")

    try:
        async with transaction(db):
            org = Organization(name=body.name, slug=body.slug)
            db.add(org)
            await db.flush()
            admin = User(
                tenant_id=org.id,
                email=body.admin_email,
                username=body.admin_username,
                first_name=body.admin_first_name,
                last_name=body.admin_last_name,
                hashed_password=get_password_hash(body.admin_password),
                role=UserRole.ADMIN,
                is_active=True,
                is_superuser=False,
            )
            db.add(admin)
            await db.flush()
            AuditService(db).add(
                tenant_id=org.id,
                user_id=current_user.id,
                action="organization.created",
                entity_type="Organization",
                entity_id=org.id,
                changes={"name": org.name, "slug": org.slug, "admin_user_id": admin.id},
            )
    except IntegrityError:
        # A concurrent request won the race for the same slug/email/username
        raise HTTPException(status.HTTP_409_CONFLICT, detail="Organisation or admin already exists")

    return OrganizationCreated(
        id=org.id, name=org.name, slug=org.slug, plan=org.plan, is_active=org.is_active,
        max_users=org.max_users, max_containers=org.max_containers, admin_user_id=admin.id,
    )


@router.get(
    "/me",
    response_model=OrganizationOut,
    summary="Your organisation",
)
async def my_organization(db: DBDep, current_user: CurrentUser):
    org = (
        await db.execute(select(Organization).where(Organization.id == current_user.tenant_id))
    ).scalar_one_or_none()
    if org is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Organisation not found")
    return org
