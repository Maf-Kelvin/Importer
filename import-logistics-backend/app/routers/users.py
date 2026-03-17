# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select

from app.routers.deps import AdminUser, CurrentUser, DBDep
from app.schemas.common import PagedResponse, PaginationParams
from app.schemas.user import UserAdminCreate, UserAdminUpdate, UserInDB
from app.services.auth_service import AuthService
from app.models.user import User

router = APIRouter()


@router.get(
    "/",
    response_model=PagedResponse[UserInDB],
    summary="List all users (admin only)",
)
async def list_users(
    db: DBDep,
    _: AdminUser,
    params: PaginationParams = Depends(),
):
    total_result = await db.execute(select(func.count(User.id)))
    total = total_result.scalar_one()

    result = await db.execute(
        select(User).offset(params.offset).limit(params.limit)
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
    update: UserAdminUpdate,
    db: DBDep,
    current_user: CurrentUser,
):
    svc = AuthService(db)
    # Strip role and is_active — users cannot self-escalate
    data = update.model_dump(exclude_unset=True, exclude={"role", "is_active"})
    return await svc.update_user(current_user, data)


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
        return await svc.create_user(user_create, tenant_id=current_user.tenant_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get(
    "/{user_id}",
    response_model=UserInDB,
    summary="Get user by ID (admin only)",
)
async def get_user(user_id: int, db: DBDep, _: AdminUser):
    result = await db.execute(select(User).where(User.id == user_id))
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
    _: AdminUser,
):
    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    svc  = AuthService(db)
    data = update.model_dump(exclude_unset=True)
    return await svc.update_user(user, data)


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
    result = await db.execute(select(User).where(User.id == user_id))
    user   = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    svc = AuthService(db)
    await svc.update_user(user, {"is_active": False})
    return {"message": f"User {user_id} deactivated"}