# app/services/file_service.py
import asyncio
import logging
import os
import re
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

_EXTENSION_FOR_MIME = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}
_KEY_RE = re.compile(r"^(\d+)/(\d+)/[0-9a-f]{32}\.(?:jpg|png|webp|pdf)$")


class FileService:
    """
    Abstracted file storage backend.
    Switches between local, S3, and Cloudflare R2 via STORAGE_BACKEND config.
    """

    def __init__(self) -> None:
        self._backend = settings.STORAGE_BACKEND.lower()

    async def upload(self, file: UploadFile, uploader_id: int, tenant_id: int) -> dict[str, Any]:
        # 1. Size validation - read in chunks so a huge upload cannot exhaust memory
        content = bytearray()
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            content.extend(chunk)
            if len(content) > settings.MAX_UPLOAD_SIZE:
                raise ValueError(f"File too large (max {settings.MAX_UPLOAD_SIZE} bytes)")
        content = bytes(content)
        if not content:
            raise ValueError("Empty file")

        # 2. MIME type validation via libmagic (not filename extension)
        detected_mime = magic.from_buffer(content, mime=True)
        if detected_mime not in ALLOWED_MIME_TYPES or detected_mime not in _EXTENSION_FOR_MIME:
            raise ValueError(
                f"File type not allowed: {detected_mime}. "
                f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            )

        # 3. Server-chosen key: tenant/user/random + extension from the VERIFIED type
        #    (never from the client's filename)
        safe_name = f"{tenant_id}/{uploader_id}/{uuid.uuid4().hex}{_EXTENSION_FOR_MIME[detected_mime]}"

        # 4. Dispatch to backend
        if self._backend == "s3":
            await self._upload_s3(safe_name, content, detected_mime)
        elif self._backend == "r2":
            await self._upload_r2(safe_name, content, detected_mime)
        else:
            await self._upload_local(safe_name, content)

        logger.info(
            "File uploaded: key=%s size=%d mime=%s uploader=%d tenant=%d",
            safe_name, len(content), detected_mime, uploader_id, tenant_id,
        )
        return {
            "file_key":  safe_name,
            "file_url":  f"/api/v1/files/{safe_name}",   # authenticated download endpoint
            "file_size": len(content),
            "mime_type": detected_mime,
        }

    @staticmethod
    def parse_key(file_key: str) -> tuple[int, int]:
        """Validate a storage key and return (tenant_id, uploader_id).
        Rejects anything that is not exactly what upload() produces, which also
        rules out path traversal ('..', absolute paths, backslashes)."""
        m = _KEY_RE.match(file_key or "")
        if not m:
            raise ValueError("Invalid file key")
        return int(m.group(1)), int(m.group(2))

    async def delete(self, file_key: str, tenant_id: int, user_id: int, can_manage: bool) -> None:
        key_tenant, key_uploader = self.parse_key(file_key)
        if key_tenant != tenant_id or (key_uploader != user_id and not can_manage):
            raise PermissionError("File not found")   # same message: do not reveal existence
        if self._backend == "s3":
            await self._delete_s3(file_key)
        elif self._backend == "r2":
            await self._delete_r2(file_key)
        else:
            await self._delete_local(file_key)
        logger.info("File deleted: key=%s by user=%d", file_key, user_id)

    def local_path(self, file_key: str, tenant_id: int) -> Path:
        """Filesystem path of a LOCAL file the caller's tenant owns (else raises)."""
        key_tenant, _ = self.parse_key(file_key)
        if key_tenant != tenant_id:
            raise PermissionError("File not found")
        base = Path(settings.UPLOAD_DIR).resolve()
        path = (base / file_key).resolve()
        if base not in path.parents:
            raise ValueError("Invalid file key")
        return path

    # ------------------------------------------------------------------
    # Local backend
    # ------------------------------------------------------------------
    async def _upload_local(self, key: str, content: bytes) -> str:
        path = Path(settings.UPLOAD_DIR) / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return f"/uploads/{key}"

    async def _delete_local(self, key: str) -> None:
        base = Path(settings.UPLOAD_DIR).resolve()
        path = (base / key).resolve()
        if base in path.parents and path.exists():
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
            await asyncio.to_thread(      # boto3 is blocking: keep it off the event loop
                s3.put_object,
                Bucket=settings.S3_BUCKET, Key=key, Body=content, ContentType=mime,
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
        await asyncio.to_thread(s3.delete_object, Bucket=settings.S3_BUCKET, Key=key)

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
        await asyncio.to_thread(
            r2.put_object,
            Bucket=settings.R2_BUCKET, Key=key, Body=content, ContentType=mime,
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
        await asyncio.to_thread(r2.delete_object, Bucket=settings.R2_BUCKET, Key=key)

    def presigned_url(self, file_key: str, tenant_id: int, expires: int = 300) -> str:
        """Short-lived download link for S3/R2 objects owned by the caller's tenant."""
        key_tenant, _ = self.parse_key(file_key)
        if key_tenant != tenant_id:
            raise PermissionError("File not found")
        import boto3
        if self._backend == "r2":
            client = boto3.client(
                "s3",
                endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name="auto",
            )
            bucket = settings.R2_BUCKET
        else:
            client = boto3.client(
                "s3", region_name=settings.S3_REGION,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
            )
            bucket = settings.S3_BUCKET
        return client.generate_presigned_url(
            "get_object", Params={"Bucket": bucket, "Key": file_key}, ExpiresIn=expires
        )

