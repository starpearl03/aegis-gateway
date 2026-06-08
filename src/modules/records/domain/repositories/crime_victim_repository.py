# ===== criminal/repositories/crime_victim_repository.py =====
from typing import List

from src.modules.records.domain.models.crime_victim import CrimeVictim
from src.shared.data.base.repository import BaseRepository


class CrimeVictimRepository(BaseRepository[CrimeVictim]):
    """Repository for CrimeVictim model"""

    def __init__(self):
        super().__init__(CrimeVictim)

    def find_by_crime(self, crime_id: str) -> List[CrimeVictim]:
        """Find all victims of a specific crime"""
        return self.find_many_by({"crime_id": crime_id})

    def find_by_person(self, person_id: str) -> List[CrimeVictim]:
        """Find all crimes where a person was a victim"""
        return self.find_many_by({"person_id": person_id})

    def is_victim(self, crime_id: str, person_id: str) -> bool:
        """Check if a person is a victim of a specific crime"""
        return self.exists({"crime_id": crime_id, "person_id": person_id})
