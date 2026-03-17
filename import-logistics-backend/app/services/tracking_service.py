# app/services/tracking_service.py
import logging
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import transaction
from app.models.container import Container
from app.models.tracking import TrackingRecord, TrackingStatus
from app.models.user import User, UserRole
from app.schemas.tracking import NotificationSettingsUpdate, TrackingStatusResponse

logger = logging.getLogger(__name__)


class TrackingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Update tracking for one container
    # ------------------------------------------------------------------
    async def update_container_tracking(
        self, container_id: int
    ) -> dict[str, Any]:
        result = await self.db.execute(
            select(Container).where(Container.id == container_id)
        )
        container = result.scalar_one_or_none()
        if not container or not container.msc_container_number:
            return {"error": "Container not found or MSC number not set"}

        tracking_data = await self._fetch_msc_tracking(container.msc_container_number)
        if not tracking_data:
            return {"error": "No tracking data available from MSC"}

        # Safe enum coercion — was crashing on "unknown" before
        raw_status = tracking_data.get("status", "unknown")
        try:
            status = TrackingStatus(raw_status)
        except ValueError:
            status = TrackingStatus.UNKNOWN
            logger.warning("Unknown tracking status received: %s", raw_status)

        async with transaction(self.db):
            record = TrackingRecord(
                tenant_id=container.tenant_id,
                container_id=container_id,
                status=status,
                location=tracking_data.get("location"),
                vessel_name=tracking_data.get("vessel_name"),
                voyage_number=tracking_data.get("voyage_number"),
                status_date=tracking_data.get("status_date"),
                estimated_arrival=tracking_data.get("estimated_arrival"),
                actual_arrival=tracking_data.get("actual_arrival"),
                raw_data=tracking_data,
            )
            self.db.add(record)

        logger.info(
            "Tracking updated: container_id=%d status=%s", container_id, status
        )
        return {
            "status":           "success",
            "container_id":     container_id,
            "tracking_status":  status.value,
            "location":         tracking_data.get("location"),
        }

    # ------------------------------------------------------------------
    # Update all active containers — was missing before
    # ------------------------------------------------------------------
    async def update_all_tracking(self) -> dict[str, Any]:
        result = await self.db.execute(
            select(Container).where(
                Container.is_shipped == True,        # noqa: E712
                Container.deleted_at.is_(None),
                Container.msc_container_number.isnot(None),
            )
        )
        containers = result.scalars().all()

        updated = 0
        errors  = 0
        for container in containers:
            try:
                res = await self.update_container_tracking(container.id)
                if res.get("status") == "success":
                    updated += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error(
                    "Tracking update failed for container_id=%d: %s",
                    container.id, e,
                )
                errors += 1

        return {
            "status":  "success",
            "updated": updated,
            "errors":  errors,
            "total":   len(containers),
        }

    # ------------------------------------------------------------------
    # History + current status
    # ------------------------------------------------------------------
    async def get_tracking_history(
        self, container_id: int, current_user: User
    ) -> list[TrackingRecord]:
        container = await self._get_container_with_permission(
            container_id, current_user
        )
        if not container:
            return []

        result = await self.db.execute(
            select(TrackingRecord)
            .where(TrackingRecord.container_id == container_id)
            .order_by(TrackingRecord.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_current_status(
        self, container_id: int, current_user: User
    ) -> Optional[TrackingStatusResponse]:
        history = await self.get_tracking_history(container_id, current_user)
        if not history:
            return None
        latest = history[0]
        return TrackingStatusResponse(
            status=latest.status.value,
            location=latest.location,
            vessel_name=latest.vessel_name,
            voyage_number=latest.voyage_number,
            status_date=latest.status_date,
            estimated_arrival=latest.estimated_arrival,
            last_updated=latest.created_at,
        )

    # ------------------------------------------------------------------
    # Notification settings — was missing before
    # ------------------------------------------------------------------
    async def update_notification_settings(
        self,
        container_id: int,
        data: NotificationSettingsUpdate,
        current_user: User,
    ) -> Optional[dict[str, Any]]:
        container = await self._get_container_with_permission(
            container_id, current_user
        )
        if not container:
            return None

        # Store settings in container extra_data
        async with transaction(self.db):
            extra = container.extra_data or {}
            extra["notifications"] = {
                "enabled":              data.enable_notifications,
                "interval_days":        data.notification_interval,
                "email_notifications":  data.email_notifications,
                "webhook_url":          data.webhook_url,
            }
            container.extra_data = extra

        logger.info(
            "Notification settings updated: container_id=%d", container_id
        )
        return {"status": "updated", "settings": extra["notifications"]}

    # ------------------------------------------------------------------
    # MSC API
    # ------------------------------------------------------------------
    async def _fetch_msc_tracking(
        self, msc_number: str
    ) -> Optional[dict[str, Any]]:
        if not settings.MSC_API_KEY:
            return self._mock_tracking_data()

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(
                    f"{settings.MSC_API_URL}/tracking/{msc_number}",
                    headers={"Authorization": f"Bearer {settings.MSC_API_KEY}"},
                )
                if resp.status_code == 200:
                    return resp.json()
                logger.warning("MSC API returned %d for %s", resp.status_code, msc_number)
        except Exception as e:
            logger.error("MSC API request failed: %s", e)

        return None

    def _mock_tracking_data(self) -> dict[str, Any]:
        """Deterministic mock — no random() so tests are stable."""
        return {
            "status":       "in_transit",
            "location":     "Atlantic Ocean",
            "vessel_name":  "MSC VESSEL 001",
            "voyage_number": "V1001",
            "status_date":  None,
            "estimated_arrival": None,
            "actual_arrival":    None,
        }

    async def _get_container_with_permission(
        self, container_id: int, current_user: User
    ) -> Optional[Container]:
        q = select(Container).where(
            Container.id        == container_id,
            Container.tenant_id == current_user.tenant_id,
            Container.deleted_at.is_(None),
        )
        if current_user.role == UserRole.CLERK:
            q = q.where(Container.owner_id == current_user.id)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()