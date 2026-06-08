# ===== criminal/repositories/punishment_repository.py =====
from typing import List

from src.modules.records.domain.models.enums import PunishmentType, PunishmentStatus
from src.modules.records.domain.models.punishment import Punishment
from src.shared.data.base.repository import BaseRepository


class PunishmentRepository(BaseRepository[Punishment]):
    """Repository for Punishment model"""

    def __init__(self):
        super().__init__(Punishment)

    def find_by_crime(self, crime_id: str) -> List[Punishment]:
        """Find all punishments for a specific crime"""
        return self.find_many_by({"crime_id": crime_id})

    def find_by_type(self, punishment_type: PunishmentType) -> List[Punishment]:
        """Find all punishments of a specific type"""
        return self.find_many_by({"type": punishment_type})

    def find_by_status(self, status: PunishmentStatus) -> List[Punishment]:
        """Find all punishments by status"""
        return self.find_many_by({"status": status})

    def find_active_punishments(self) -> List[Punishment]:
        """Find all currently active punishments"""
        return self.find_by_status(PunishmentStatus.ACTIVE)

    def find_pending_punishments(self) -> List[Punishment]:
        """Find all pending punishments"""
        return self.find_by_status(PunishmentStatus.PENDING)

    def find_unpaid_fines(self) -> List[Punishment]:
        """Find all unpaid fines"""
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.type == PunishmentType.FINE,
            self.model.amount_paid < self.model.amount
        ).all()

    def find_by_location(self, location_id: str) -> List[Punishment]:
        """Find punishments at a specific location (e.g., jail, community service site)"""
        return self.find_many_by({"location_id": location_id})