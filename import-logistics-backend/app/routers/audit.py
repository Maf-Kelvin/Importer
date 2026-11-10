# app/routers/audit.py
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.routers.deps import AdminUser, DBDep
from app.schemas.audit import AuditLogOut
from app.schemas.common import PagedResponse, PaginationParams
from app.services.audit_service import AuditService

router = APIRouter()


@router.get(
    "/",
    response_model=PagedResponse[AuditLogOut],
    summary="Audit trail for your organisation (admin only, newest first)",
)
async def list_audit_logs(
    db: DBDep,
    current_user: AdminUser,
    params: PaginationParams = Depends(),
    action: Optional[str] = Query(None, description="Action prefix, e.g. 'expense.' or 'user.created'"),
    entity_type: Optional[str] = Query(None, description="e.g. Container, Item, ContainerExpense, User"),
    user_id: Optional[int] = Query(None, description="Only entries made by this user"),
):
    rows, total = await AuditService(db).list_for_tenant(
        current_user.tenant_id, params, action, entity_type, user_id
    )
    return PagedResponse.create(rows, total, params)
