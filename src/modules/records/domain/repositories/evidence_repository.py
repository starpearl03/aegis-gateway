# src/modules/records/infrastructure/repositories/evidence_repository.py
from typing import List

from src.modules.records.domain.models.evidence import Evidence, EvidenceFaceVector
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
        return self.model.query.join(
            self.model.face_vectors
        ).filter(
            self.model.is_deleted == False,
            self.model.crime_id == crime_id
        ).distinct().all()

    def find_by_storage_location(self, storage_location: str) -> List[Evidence]:
        """Find evidence by storage location"""
        return self.find_many_by({"storage_location": storage_location})

    def count_by_crime(self, crime_id: str) -> int:
        """Count evidence for a specific crime"""
        return self.count({"crime_id": crime_id})

class FaceVectorRepository(BaseRepository[EvidenceFaceVector]):
    """Repository for FaceVector model"""

    def __init__(self):
        super().__init__(EvidenceFaceVector)

    def find_by_evidence_id(self, evidence_id: str, include_deleted: bool = False) -> List[EvidenceFaceVector]:
        """
        Find all face vectors for a specific evidence.

        Args:
            evidence_id: The ID of the evidence
            include_deleted: Whether to include soft-deleted records

        Returns:
            List of face vectors for the evidence
        """
        return self.find_many_by({"evidence_id": evidence_id}, include_deleted=include_deleted)

    def count_by_evidence_id(self, evidence_id: str) -> int:
        """
        Count face vectors for a specific evidence.

        Args:
            evidence_id: The ID of the evidence

        Returns:
            Number of face vectors for the evidence
        """
        return self.count({"evidence_id": evidence_id})

    def delete_by_evidence_id(self, evidence_id: str) -> None:
        """
        Soft delete all face vectors for a specific evidence.

        Args:
            evidence_id: The ID of the evidence
        """
        face_vectors = self.find_by_evidence_id(evidence_id)
        if face_vectors:
            self.delete_many(face_vectors)

    def hard_delete_by_evidence_id(self, evidence_id: str) -> None:
        """
        Permanently delete all face vectors for a specific evidence.

        Args:
            evidence_id: The ID of the evidence
        """
        face_vectors = self.find_by_evidence_id(evidence_id)
        if face_vectors:
            self.hard_delete_many(face_vectors)