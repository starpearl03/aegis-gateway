# src/modules/analysis/data/repositories/alert_broadcast_repository.py
from typing import List

from src.modules.crime_analysis.domain.models.alert_broadcast import AlertBroadcast
from src.modules.crime_analysis.domain.models.enums import BroadcastStatus
from src.shared.data.base.repository import BaseRepository


class AlertBroadcastRepository(BaseRepository[AlertBroadcast]):
    """Repository for AlertBroadcast model"""

    def __init__(self):
        super().__init__(AlertBroadcast)

    def find_by_hotspot(self, hotspot_id: str) -> List[AlertBroadcast]:
        """Find all alerts for a specific hotspot"""
        return self.find_many_by({"hotspot_id": hotspot_id})

    def find_by_status(self, status: BroadcastStatus) -> List[AlertBroadcast]:
        """Find all alerts by status"""
        return self.find_many_by({"status": status})

    def find_pending_alerts(self) -> List[AlertBroadcast]:
        """Find all pending alerts"""
        return self.find_many_by({"status": BroadcastStatus.PENDING})

    def find_sent_alerts(self) -> List[AlertBroadcast]:
        """Find all sent alerts"""
        return self.find_many_by({"status": BroadcastStatus.SENT})

    def find_failed_alerts(self) -> List[AlertBroadcast]:
        """Find all failed alerts"""
        return self.find_many_by({"status": BroadcastStatus.FAILED})

    def find_recent_alerts(self, limit: int = 10) -> List[AlertBroadcast]:
        """
        Find most recently sent alerts.

        Args:
            limit: Number of recent alerts to return

        Returns:
            List of recent alerts
        """
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.sent_at.isnot(None)
        ).order_by(self.model.sent_at.desc()).limit(limit).all()