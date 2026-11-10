# app/routers/files.py
import mimetypes

from fastapi import APIRouter, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse

from app.models.user import UserRole
from app.routers.deps import ClerkUser, CurrentUser, DBDep
from app.services.audit_service import AuditService
from app.services.file_service import FileService

router = APIRouter()

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")


@router.post(
    "/upload",
    summary="Upload a file (item photo, document, invoice)",
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(file: UploadFile, db: DBDep, current_user: ClerkUser):
    svc = FileService()
    try:
        return await svc.upload(
            file, uploader_id=current_user.id, tenant_id=current_user.tenant_id
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/{file_key:path}",
    summary="Download a file (your organisation's files only)",
)
async def download_file(file_key: str, current_user: CurrentUser):
    svc = FileService()
    try:
        if svc._backend in ("s3", "r2"):
            return RedirectResponse(
                svc.presigned_url(file_key, current_user.tenant_id), status_code=302
            )
        path = svc.local_path(file_key, current_user.tenant_id)
    except (ValueError, PermissionError):
        raise _NOT_FOUND
    if not path.is_file():
        raise _NOT_FOUND
    media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(path, media_type=media_type, headers={"X-Content-Type-Options": "nosniff"})


@router.delete(
    "/{file_key:path}",
    summary="Delete an uploaded file (your own, or any in your organisation if manager/admin)",
)
async def delete_file(file_key: str, db: DBDep, current_user: ClerkUser):
    svc = FileService()
    can_manage = current_user.is_superuser or current_user.role in (UserRole.ADMIN, UserRole.MANAGER)
    try:
        await svc.delete(file_key, current_user.tenant_id, current_user.id, can_manage)
    except (ValueError, PermissionError):
        raise _NOT_FOUND
    await AuditService(db).record(
        tenant_id=current_user.tenant_id, user_id=current_user.id, action="file.deleted",
        entity_type="File", changes={"file_key": file_key},
    )
    return {"message": "File deleted"}
