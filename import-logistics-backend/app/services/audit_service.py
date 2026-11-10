# app/services/audit_service.py
"""Append-only audit trail: who did what, to which record, from where."""
import logging
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import request_context
from app.core.database import transaction
from app.models.analytics import AuditLog
from app.schemas.common import PaginationParams
from app.utils.audit import redact, to_jsonable

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def add(
        self,
        *,
        tenant_id: int,
        user_id: Optional[int],
        action: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        changes: Optional[dict[str, Any]] = None,
    ) -> None:
        """Stage an audit row in the CURRENT transaction (no commit).

        Call it inside the same `async with transaction(...)` as the change,
        so the change and its audit record are saved together or not at all.
        """
        self.db.add(
            AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                ip_address=request_context.client_ip.get(),
                user_agent=request_context.user_agent.get(),
                extra_data=redact(to_jsonable_dict(changes)) if changes else None,
            )
        )

    async def record(self, **kwargs: Any) -> None:
        """Write an audit row in its own transaction."""
        async with transaction(self.db):
            self.add(**kwargs)

    async def list_for_tenant(
        self,
        tenant_id: int,
        params: PaginationParams,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> tuple[list[AuditLog], int]:
        conditions = [AuditLog.tenant_id == tenant_id]
        if action:
            conditions.append(AuditLog.action.startswith(action))
        if entity_type:
            conditions.append(AuditLog.entity_type == entity_type)
        if user_id is not None:
            conditions.append(AuditLog.user_id == user_id)

        total = (
            await self.db.execute(select(func.count(AuditLog.id)).where(*conditions))
        ).scalar_one()
        rows = (
            await self.db.execute(
                select(AuditLog)
                .where(*conditions)
                .order_by(AuditLog.id.desc())
                .offset(params.offset)
                .limit(params.limit)
            )
        ).scalars().all()
        return list(rows), total


def to_jsonable_dict(data: dict[str, Any]) -> dict[str, Any]:
    return {k: to_jsonable(v) if not isinstance(v, (dict, list)) else v for k, v in data.items()}
