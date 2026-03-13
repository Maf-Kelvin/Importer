# app/services/tracking_service.py
import requests
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.container import Container
from app.models.tracking import TrackingRecord, TrackingStatus
from app.models.user import User, UserRole
from app.core.config import settings
from datetime import datetime


class TrackingService:
    def __init__(self, db: Session):
        self.db = db
    
    def update_container_tracking(self, container_id: int) -> Dict[str, Any]:
        """Update tracking information for a container."""
        container = self.db.query(Container).filter(Container.id == container_id).first()
        if not container or not container.msc_container_number:
            return {'error': 'Container not found or MSC number not set'}
        
        try:
            # Call MSC API (simplified example)
            tracking_data = self._fetch_msc_tracking(container.msc_container_number)
            
            if tracking_data:
                # Create new tracking record
                tracking_record = TrackingRecord(
                    container_id=container_id,
                    status=TrackingStatus(tracking_data.get('status', 'unknown')),
                    location=tracking_data.get('location'),
                    vessel_name=tracking_data.get('vessel_name'),
                    voyage_number=tracking_data.get('voyage_number'),
                    status_date=tracking_data.get('status_date'),
                    estimated_arrival=tracking_data.get('estimated_arrival'),
                    actual_arrival=tracking_data.get('actual_arrival'),
                    raw_data=tracking_data
                )
                
                self.db.add(tracking_record)
                self.db.commit()
                
                return {
                    'status': 'success',
                    'container_id': container_id,
                    'tracking_status': tracking_data.get('status'),
                    'location': tracking_data.get('location')
                }
            
        except Exception as e:
            return {'error': f'Failed to update tracking: {str(e)}'}
        
        return {'error': 'No tracking data available'}
    
    def _fetch_msc_tracking(self, msc_number: str) -> Optional[Dict[str, Any]]:
        """Fetch tracking data from MSC API."""
        if not settings.MSC_API_KEY:
            # Return mock data for development
            return self._get_mock_tracking_data()
        
        try:
            headers = {
                'Authorization': f'Bearer {settings.MSC_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(
                f"{settings.MSC_API_URL}/tracking/{msc_number}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
                
        except Exception as e:
            print(f"Error fetching MSC tracking: {e}")
        
        return None
    
    def _get_mock_tracking_data(self) -> Dict[str, Any]:
        """Return mock tracking data for development."""
        import random
        
        statuses = ['booked', 'loaded', 'departed', 'in_transit', 'arrived', 'discharged']
        locations = ['Lagos Port', 'Atlantic Ocean', 'Hamburg Port', 'Prague Terminal']
        
        return {
            'status': random.choice(statuses),
            'location': random.choice(locations),
            'vessel_name': 'MSC VESSEL ' + str(random.randint(100, 999)),
            'voyage_number': 'V' + str(random.randint(1000, 9999)),
            'status_date': datetime.now().isoformat(),
            'estimated_arrival': '2024-02-15T10:00:00Z',
            'last_updated': datetime.now().isoformat()
        }
    
    def get_tracking_history(self, container_id: int, current_user: User) -> List[TrackingRecord]:
        """Get tracking history for a container."""
        # Check permissions
        container = self.db.query(Container).filter(Container.id == container_id).first()
        if not container:
            return []
        
        if current_user.role == UserRole.CLERK and container.owner_id != current_user.id:
            return []
        
        return self.db.query(TrackingRecord).filter(
            TrackingRecord.container_id == container_id
        ).order_by(TrackingRecord.created_at.desc()).all()
    
    def get_current_status(self, container_id: int, current_user: User) -> Optional[Dict[str, Any]]:
        """Get current tracking status for a container."""
        history = self.get_tracking_history(container_id, current_user)
        if not history:
            return None
        
        latest = history[0]
        return {
            'status': latest.status.value,
            'location': latest.location,
            'vessel_name': latest.vessel_name,
            'voyage_number': latest.voyage_number,
            'status_date': latest.status_date.isoformat() if latest.status_date else None,
            'estimated_arrival': latest.estimated_arrival.isoformat() if latest.estimated_arrival else None,
            'last_updated': latest.created_at.isoformat()
        }