# app/models/idempotency.py
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class IdempotencyKey(BaseModel):
    """Durable record of an idempotent request (the source of truth).

    key         tenant:user + hash of the client's Idempotency-Key   (UNIQUE: the real guarantee)
    fingerprint hash of method + path + query + body
    state       'processing' while the first request runs, then 'completed'
    response    stored 2xx response (status, content type, base64 body) once completed
    expires_at  a stuck 'processing' claim becomes retryable after this; a completed
                record is deleted by the nightly purge task
    """
    __tablename__ = "idempotency_keys"

    key:         Mapped[str]            = mapped_column(String(255), nullable=False, unique=True)
    fingerprint: Mapped[str]            = mapped_column(String(64), nullable=False)
    state:       Mapped[str]            = mapped_column(String(16), nullable=False)
    owner:       Mapped[str]            = mapped_column(String(32), nullable=False)
    response:    Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    expires_at:  Mapped[datetime]       = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_idempotency_expires_at", "expires_at"),)
