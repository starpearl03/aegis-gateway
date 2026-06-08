# ===== criminal/repositories/evidence_repository.py =====
from typing import List

from src.modules.records.domain.models.evidence import Evidence
from src.shared.data.base.repository import BaseRepository


class EvidenceRepository(BaseRepository[Evidence]):
    """Repository for Evidence model"""

    def __init__(self):
        super().__init__(Evidence)

    def find_by_crime(self, crime_id: str) -> List[Evidence]:
        """Find all evidence for a specific crime"""
        return self.find_many_by({"crime_id": crime_id})

    def find_by_type(self, evidence_type: str) -> List[Evidence]:
        """Find all evidence of a specific type"""
        return self.find_many_by({"type": evidence_type})

    def find_by_collector(self, user_id: str) -> List[Evidence]:
        """Find all evidence collected by a specific user"""
        return self.find_many_by({"collected_by": user_id})

    def find_with_facial_data(self, crime_id: str) -> List[Evidence]:
        """Find all evidence with facial recognition data for a crime"""
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.crime_id == crime_id,
            self.model.face_vectors.isnot(None)
        ).all()

    def find_by_storage_location(self, storage_location: str) -> List[Evidence]:
        """Find evidence by storage location"""
        return self.find_many_by({"storage_location": storage_location})