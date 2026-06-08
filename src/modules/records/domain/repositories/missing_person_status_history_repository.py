# ===== missing_person/repositories/missing_person_status_history_repository.py =====
from typing import List

from src.modules.records.domain.models.missing_person_status_history import MissingPersonStatusHistory
from src.shared.data.base.repository import BaseRepository


class MissingPersonStatusHistoryRepository(BaseRepository[MissingPersonStatusHistory]):
    """Repository for MissingPersonStatusHistory model"""

    def __init__(self):
        super().__init__(MissingPersonStatusHistory)

    def find_by_missing_person(self, missing_person_id: str) -> List[MissingPersonStatusHistory]:
        """Find all status history records for a missing person"""
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.missing_person_id == missing_person_id
        ).order_by(self.model.created_at.desc()).all()

    def find_by_user(self, user_id: str) -> List[MissingPersonStatusHistory]:
        """Find all status changes made by a specific user"""
        return self.find_many_by({"changed_by": user_id})