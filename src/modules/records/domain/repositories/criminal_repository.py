# ===== criminal/repositories/criminal_repository.py =====
from typing import List

from src.modules.records.domain.models.criminal import Criminal
from src.shared.data.base.repository import BaseRepository


class CriminalRepository(BaseRepository[Criminal]):
    """Repository for Criminal model"""

    def __init__(self):
        super().__init__(Criminal)

    def find_wanted(self) -> List[Criminal]:
        """Find all wanted criminals"""
        return self.find_many_by({"is_wanted": True})

    def find_by_priority(self, priority_level: int) -> List[Criminal]:
        """Find criminals by priority level"""
        return self.find_many_by({"priority_level": priority_level})

    def find_high_priority_wanted(self, min_priority: int = 3) -> List[Criminal]:
        """
        Find high-priority wanted criminals.

        Args:
            min_priority: Minimum priority level (default: 3)

        Returns:
            List of high-priority wanted criminals
        """
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.is_wanted == True,
            self.model.priority_level >= min_priority
        ).order_by(self.model.priority_level.desc()).all()

    def find_by_alias(self, alias: str) -> List[Criminal]:
        """Find criminals by alias"""
        return self.find_many_by({"alias": alias})

    def find_by_gang(self, gang_affiliation: str) -> List[Criminal]:
        """Find all criminals affiliated with a specific gang"""
        return self.find_many_by({"gang_affiliation": gang_affiliation})

    def find_by_threat_level(self, threat_level: str) -> List[Criminal]:
        """Find criminals by threat level"""
        return self.find_many_by({"threat_level": threat_level})
