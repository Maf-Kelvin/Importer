# app/services/notification_service.py
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------------------
# Email message dataclass
# ------------------------------------------------------------------------------
@dataclass
class EmailMessage:
    to_email: str
    subject:  str
    body:     str
    html:     str | None = None


# ------------------------------------------------------------------------------
# Abstract provider — swap implementation via EMAIL_PROVIDER config
# ------------------------------------------------------------------------------
class EmailProvider(ABC):
    @abstractmethod
    async def send(self, msg: EmailMessage) -> dict[str, Any]:
        ...


class SMTPProvider(EmailProvider):
    async def send(self, msg: EmailMessage) -> dict[str, Any]:
        mime = MIMEMultipart("alternative")
        mime["From"]    = settings.EMAILS_FROM_EMAIL or ""
        mime["To"]      = msg.to_email
        mime["Subject"] = msg.subject
        mime.attach(MIMEText(msg.body, "plain"))
        if msg.html:
            mime.attach(MIMEText(msg.html, "html"))

        try:
            await aiosmtplib.send(
                mime,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_TLS,
            )
            return {"status": "success", "sent_to": msg.to_email}
        except Exception as e:
            logger.error("SMTP send failed to %s: %s", msg.to_email, e)
            return {"status": "error", "reason": str(e)}


class SendGridProvider(EmailProvider):
    async def send(self, msg: EmailMessage) -> dict[str, Any]:
        try:
            import httpx
            payload = {
                "personalizations": [{"to": [{"email": msg.to_email}]}],
                "from":    {"email": settings.EMAILS_FROM_EMAIL},
                "subject": msg.subject,
                "content": [{"type": "text/plain", "value": msg.body}],
            }
            if msg.html:
                payload["content"].append({"type": "text/html", "value": msg.html})

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
                )
                if resp.status_code in (200, 202):
                    return {"status": "success", "sent_to": msg.to_email}
                return {"status": "error", "reason": resp.text}
        except Exception as e:
            logger.error("SendGrid send failed: %s", e)
            return {"status": "error", "reason": str(e)}


class MailgunProvider(EmailProvider):
    async def send(self, msg: EmailMessage) -> dict[str, Any]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"https://api.mailgun.net/v3/{settings.MAILGUN_DOMAIN}/messages",
                    auth=("api", settings.MAILGUN_API_KEY or ""),
                    data={
                        "from":    settings.EMAILS_FROM_EMAIL,
                        "to":      msg.to_email,
                        "subject": msg.subject,
                        "text":    msg.body,
                        "html":    msg.html or "",
                    },
                )
                if resp.status_code == 200:
                    return {"status": "success", "sent_to": msg.to_email}
                return {"status": "error", "reason": resp.text}
        except Exception as e:
            logger.error("Mailgun send failed: %s", e)
            return {"status": "error", "reason": str(e)}


def _get_provider() -> EmailProvider:
    p = settings.EMAIL_PROVIDER.lower()
    if p == "sendgrid":
        return SendGridProvider()
    if p == "mailgun":
        return MailgunProvider()
    return SMTPProvider()


# ------------------------------------------------------------------------------
# Notification service
# ------------------------------------------------------------------------------
class NotificationService:

    def __init__(self) -> None:
        self._provider = _get_provider()

    async def send_tracking_notification(
        self, container_id: int
    ) -> dict[str, Any]:
        if not settings.EMAIL_ENABLED:
            return {"status": "skipped", "reason": "Email disabled"}

        from app.core.database import AsyncSessionLocal
        from app.models.container import Container
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Container).where(Container.id == container_id)
            )
            container = result.scalar_one_or_none()
            if not container:
                return {"status": "error", "reason": "Container not found"}

            # Load owner separately (avoid lazy load in async context)
            from app.models.user import User
            owner_res = await db.execute(
                select(User).where(User.id == container.owner_id)
            )
            owner = owner_res.scalar_one_or_none()
            if not owner:
                return {"status": "error", "reason": "Owner not found"}

        msg = EmailMessage(
            to_email=owner.email,
            subject=f"Container {container.name} — Status Update",
            body=(
                f"Dear {owner.first_name},\n\n"
                f"Your container {container.name} has a new status update.\n"
                f"Please log in to view the latest tracking information.\n\n"
                f"Best regards,\n{settings.EMAILS_FROM_NAME}"
            ),
        )
        return await self._provider.send(msg)

    async def send_custom_notification(
        self,
        container_id: int,
        message: str,
        recipients: list[str],
    ) -> dict[str, Any]:
        """Was missing before — called by notification_worker."""
        if not settings.EMAIL_ENABLED:
            return {"status": "skipped", "reason": "Email disabled"}

        results = []
        for email in recipients:
            msg = EmailMessage(
                to_email=email,
                subject="Import Logistics — Notification",
                body=message,
            )
            result = await self._provider.send(msg)
            results.append(result)

        success = sum(1 for r in results if r.get("status") == "success")
        logger.info(
            "Custom notification sent: container_id=%d recipients=%d success=%d",
            container_id, len(recipients), success,
        )
        return {"status": "success", "sent": success, "total": len(recipients)}