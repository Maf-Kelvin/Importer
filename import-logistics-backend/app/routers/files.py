# app/routers/files.py
from fastapi import APIRouter, HTTPException, UploadFile, status

from app.routers.deps import ClerkUser, DBDep
from app.services.file_service import FileService

router = APIRouter()


@router.post(
    "/upload",
    summary="Upload a file (item photo, document, invoice)",
    status_code=status.HTTP_201_CREATED,
)
async def upload_file(
    file: UploadFile,
    db: DBDep,
    current_user: ClerkUser,
):
    svc = FileService()
    try:
        result = await svc.upload(file, uploader_id=current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{file_key:path}",
    summary="Delete an uploaded file",
)
async def delete_file(
    file_key: str,
    db: DBDep,
    current_user: ClerkUser,
):
    svc = FileService()
    try:
        await svc.delete(file_key)
        return {"message": "File deleted"}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))