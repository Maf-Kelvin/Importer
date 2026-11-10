# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.routers.deps import AdminUser, CurrentUser, DBDep
from app.schemas.common import PagedResponse, PaginationParams
from app.schemas.user import UserAdminCreate, UserAdminUpdate, UserUpdate, UserInDB
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.models.user import User
from app.utils.audit import diff, snapshot

USER_FIELDS = ("email", "username", "first_name", "last_name", "role", "is_active")

router = APIRouter()


@router.get(
    "/",
    response_model=PagedResponse[UserInDB],
    summary="List all users (admin only)",
)
async def list_users(
    db: DBDep,
    current_user: AdminUser,
    params: PaginationParams = Depends(),
):
    # Only users of the caller's own organisation
    total_result = await db.execute(
        select(func.count(User.id)).where(User.tenant_id == current_user.tenant_id)
    )
    total = total_result.scalar_one()

    result = await db.execute(
        select(User)
        .where(User.tenant_id == current_user.tenant_id)
        .order_by(User.id)
        .offset(params.offset)
        .limit(params.limit)
    )
    users = list(result.scalars().all())

    return PagedResponse.create(users, total, params)


@router.get(
    "/me",
    response_model=UserInDB,
    summary="Get current user profile",
)
async def get_me(current_user: CurrentUser):
    return current_user


@router.put(
    "/me",
    response_model=UserInDB,
    summary="Update own profile (cannot change own role)",
)
async def update_me(
    update: UserUpdate,
    db: DBDep,
    current_user: CurrentUser,
):
    svc = AuthService(db)
    # The request type (UserUpdate) has no role/is_active, so a user cannot self-escalate.
    data = {k: v for k, v in update.model_dump(exclude_unset=True).items() if v is not None}
    try:
        return await svc.update_user(current_user, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/",
    response_model=UserInDB,
    status_code=status.HTTP_201_CREATED,
    summary="Create user (admin only — any role allowed)",
)
async def create_user(
    user_create: UserAdminCreate,
    db: DBDep,
    current_user: AdminUser,
):
    svc = AuthService(db)
    try:
        user = await svc.create_user(user_create, tenant_id=current_user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    await AuditService(db).record(
        tenant_id=current_user.tenant_id, user_id=current_user.id, action="user.created",
        entity_type="User", entity_id=user.id, changes=snapshot(user, USER_FIELDS),
    )
    return user


@router.get(
    "/{user_id}",
    response_model=UserInDB,
    summary="Get user by ID (admin only)",
)
async def get_user(user_id: int, db: DBDep, current_user: AdminUser):
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put(
    "/{user_id}",
    response_model=UserInDB,
    summary="Update any user (admin only)",
)
async def update_user(
    user_id: int,
    update: UserAdminUpdate,
    db: DBDep,
    current_user: AdminUser,
):
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    svc  = AuthService(db)
    data = {k: v for k, v in update.model_dump(exclude_unset=True).items() if v is not None}
    # An admin must not demote or disable THEMSELVES: that could leave the organisation with no admin.
    # (Another admin can still do it for them, so at least one admin always remains.)
    if user.id == current_user.id and (
        ("role" in data and data["role"] != user.role) or data.get("is_active") is False
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You cannot change your own role or deactivate your own account. Ask another admin.",
        )
    before = snapshot(user, USER_FIELDS)
    try:
        updated = await svc.update_user(user, data)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    changes = diff(before, snapshot(updated, USER_FIELDS))
    if "password" in data:
        changes["password"] = {"from": None, "to": "changed"}
    await AuditService(db).record(
        tenant_id=current_user.tenant_id, user_id=current_user.id, action="user.updated",
        entity_type="User", entity_id=user.id, changes=changes,
    )
    return updated


@router.delete(
    "/{user_id}",
    summary="Deactivate user (admin only — soft disable, not delete)",
)
async def deactivate_user(user_id: int, db: DBDep, current_user: AdminUser):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account",
        )
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    svc = AuthService(db)
    await svc.update_user(user, {"is_active": False})
    await AuditService(db).record(
        tenant_id=current_user.tenant_id, user_id=current_user.id, action="user.deactivated",
        entity_type="User", entity_id=user.id,
    )
    return {"message": f"User {user_id} deactivated"}