# app/services/notification_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.models.container import Container
from app.core.database import SessionLocal


class NotificationService:
    def __init__(self):
        self.smtp_configured = all([
            settings.EMAIL_ENABLED,
            settings.SMTP_HOST,
            settings.SMTP_USER,
            settings.SMTP_PASSWORD
        ])
    
    def send_tracking_notification(self, container_id: int) -> Dict[str, Any]:
        """Send tracking notification for a container."""
        if not self.smtp_configured:
            return {'status': 'skipped', 'reason': 'Email not configured'}
        
        db = SessionLocal()
        try:
            container = db.query(Container).filter(Container.id == container_id).first()
            if not container:
                return {'status': 'error', 'reason': 'Container not found'}
            
            # Get latest tracking info
            from app.services.tracking_service import TrackingService
            tracking_service = TrackingService(db)
            current_status = tracking_service.get_current_status(container_id, container.owner)
            
            if current_status:
                # Send email notification
                subject = f"Container {container.name} Status Update"
                body = f"""
                Dear {container.owner.first_name},
                
                Your container {container.name} has a status update:
                
                Status: {current_status['status']}
                Location: {current_status.get('location', 'Unknown')}
                Vessel: {current_status.get('vessel_name', 'Unknown')}
                Last Updated: {current_status['last_updated']}
                
                Best regards,
                Import Logistics System
                """
                
                return self._send_email(
                    to_email=container.owner.email,
                    subject=subject,
                    body=body
                )
            
        finally:
            db.close()
        
        return {'status': 'error', 'reason': 'No tracking data available'}
    
    def _send_email(self, to_email: str, subject: str, body: str) -> Dict[str, Any]:
        """Send email notification."""
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.EMAILS_FROM_EMAIL
            msg['To'] = to_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            if settings.SMTP_TLS:
                server.starttls()
            
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            return {'status': 'success', 'sent_to': to_email}
            
        except Exception as e:
            return {'status': 'error', 'reason': str(e)}
