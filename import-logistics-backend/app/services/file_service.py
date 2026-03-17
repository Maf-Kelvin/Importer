# app/services/file_service.py
import logging
import os
import uuid
from pathlib import Path
from typing import Any

import magic                          # python-magic — MIME detection
from fastapi import UploadFile

from app.core.config import settings

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------------------
# MIME type whitelist
# ------------------------------------------------------------------------------
ALLOWED_MIME_TYPES = set(settings.ALLOWED_MIME_TYPES)


class FileService:
    """
    Abstracted file storage backend.
    Switches between local, S3, and Cloudflare R2 via STORAGE_BACKEND config.
    """

    def __init__(self) -> None:
        self._backend = settings.STORAGE_BACKEND.lower()

    async def upload(self, file: UploadFile, uploader_id: int) -> dict[str, Any]:
        content = await file.read()

        # 1. Size validation
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise ValueError(
                f"File too large: {len(content)} bytes "
                f"(max {settings.MAX_UPLOAD_SIZE} bytes)"
            )

        # 2. MIME type validation via libmagic (not filename extension)
        detected_mime = magic.from_buffer(content, mime=True)
        if detected_mime not in ALLOWED_MIME_TYPES:
            raise ValueError(
                f"File type not allowed: {detected_mime}. "
                f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            )

        # 3. Generate safe filename
        ext       = Path(file.filename or "upload").suffix.lower()
        safe_name = f"{uploader_id}/{uuid.uuid4().hex}{ext}"

        # 4. Dispatch to backend
        if self._backend == "s3":
            url = await self._upload_s3(safe_name, content, detected_mime)
        elif self._backend == "r2":
            url = await self._upload_r2(safe_name, content, detected_mime)
        else:
            url = await self._upload_local(safe_name, content)

        logger.info(
            "File uploaded: key=%s size=%d mime=%s uploader=%d",
            safe_name, len(content), detected_mime, uploader_id,
        )
        return {
            "file_key":  safe_name,
            "file_url":  url,
            "file_size": len(content),
            "mime_type": detected_mime,
        }

    async def delete(self, file_key: str) -> None:
        if self._backend == "s3":
            await self._delete_s3(file_key)
        elif self._backend == "r2":
            await self._delete_r2(file_key)
        else:
            await self._delete_local(file_key)
        logger.info("File deleted: key=%s", file_key)

    # ------------------------------------------------------------------
    # Local backend
    # ------------------------------------------------------------------
    async def _upload_local(self, key: str, content: bytes) -> str:
        path = Path(settings.UPLOAD_DIR) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return f"/uploads/{key}"

    async def _delete_local(self, key: str) -> None:
        path = Path(settings.UPLOAD_DIR) / key
        if path.exists():
            path.unlink()

    # ------------------------------------------------------------------
    # S3 backend
    # ------------------------------------------------------------------
    async def _upload_s3(self, key: str, content: bytes, mime: str) -> str:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError

        s3 = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )
        try:
            s3.put_object(
                Bucket=settings.S3_BUCKET,
                Key=key,
                Body=content,
                ContentType=mime,
            )
            return f"https://{settings.S3_BUCKET}.s3.{settings.S3_REGION}.amazonaws.com/{key}"
        except (BotoCoreError, ClientError) as e:
            logger.error("S3 upload failed key=%s: %s", key, e)
            raise

    async def _delete_s3(self, key: str) -> None:
        import boto3
        s3 = boto3.client(
            "s3",
            region_name=settings.S3_REGION,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
        )
        s3.delete_object(Bucket=settings.S3_BUCKET, Key=key)

    # ------------------------------------------------------------------
    # Cloudflare R2 backend (S3-compatible API)
    # ------------------------------------------------------------------
    async def _upload_r2(self, key: str, content: bytes, mime: str) -> str:
        import boto3

        r2 = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name="auto",
        )
        r2.put_object(
            Bucket=settings.R2_BUCKET,
            Key=key,
            Body=content,
            ContentType=mime,
        )
        return f"https://{settings.R2_BUCKET}.{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com/{key}"

    async def _delete_r2(self, key: str) -> None:
        import boto3
        r2 = boto3.client(
            "s3",
            endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name="auto",
        )
        r2.delete_object(Bucket=settings.R2_BUCKET, Key=key)