# ===== missing_person/repositories/reporter_repository.py =====
from typing import List, Optional

from src.modules.records.domain.models.reporter import Reporter
from src.shared.data.base.repository import BaseRepository


class ReporterRepository(BaseRepository[Reporter]):
    """Repository for Reporter model"""

    def __init__(self):
        super().__init__(Reporter)

    def find_by_missing_person(self, missing_person_id: str) -> Optional[Reporter]:
        """Find the reporter for a specific missing person"""
        return self.find_one_by({"missing_person_id": missing_person_id})

    def find_by_phone(self, phone_number: str) -> List[Reporter]:
        """Find reporters by phone number"""
        return self.find_many_by({"phone_number": phone_number})

    def find_by_email(self, email: str) -> List[Reporter]:
        """Find reporters by email"""
        return self.find_many_by({"email": email})