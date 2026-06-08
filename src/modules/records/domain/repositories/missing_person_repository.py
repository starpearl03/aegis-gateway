# ===== missing_person/repositories/missing_person_repository.py =====
from datetime import datetime
from typing import List, Optional

from src.modules.records.domain.models.enums import MissingPersonStatus
from src.modules.records.domain.models.missing_person import MissingPerson
from src.modules.records.domain.models.missing_person_status_history import MissingPersonStatusHistory
from src.modules.records.domain.repositories.missing_person_status_history_repository import \
    MissingPersonStatusHistoryRepository
from src.shared.data.base.repository import BaseRepository


class MissingPersonRepository(BaseRepository[MissingPerson]):
    """Repository for MissingPerson model"""

    def __init__(self):
        super().__init__(MissingPerson)

    def find_by_status(self, status: MissingPersonStatus) -> List[MissingPerson]:
        """Find all missing persons by status"""
        return self.find_many_by({"status": status})

    def find_active_cases(self) -> List[MissingPerson]:
        """Find all active missing person cases (status = MISSING)"""
        return self.find_by_status(MissingPersonStatus.MISSING)

    def find_by_officer(self, officer_id: str) -> List[MissingPerson]:
        """Find all cases assigned to a specific officer"""
        return self.find_many_by({"assigned_officer_id": officer_id})

    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> List[MissingPerson]:
        """
        Find missing persons last seen within a date range.

        Args:
            start_date: Start date of the range
            end_date: End date of the range

        Returns:
            List of missing persons last seen in the date range
        """
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.last_seen_date.between(start_date, end_date)
        ).all()

    def find_by_location(self, location_id: str) -> List[MissingPerson]:
        """Find missing persons last seen at a specific location"""
        return self.find_many_by({"last_seen_location_id": location_id})

    def find_recently_reported(self, days: int = 7) -> List[MissingPerson]:
        """
        Find missing persons reported within the last N days.

        Args:
            days: Number of days to look back (default: 7)

        Returns:
            List of recently reported missing persons
        """
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)

        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.created_at >= cutoff_date
        ).order_by(self.model.created_at.desc()).all()

    def update_status(self, missing_person_id: str, new_status: MissingPersonStatus,
                      changed_by: str, notes: Optional[str] = None) -> MissingPerson:
        """
        Update missing person status and create history record.

        Args:
            missing_person_id: ID of the missing person
            new_status: New status to set
            changed_by: User ID who is making the change
            notes: Optional notes about the status change

        Returns:
            Updated missing person
        """

        missing_person = self.find_by_id(missing_person_id)
        if not missing_person:
            raise ValueError(f"Missing person with ID {missing_person_id} not found")

        old_status = missing_person.status
        missing_person.status = new_status

        # Create status history record
        history = MissingPersonStatusHistory(
            missing_person_id=missing_person_id,
            old_status=old_status,
            new_status=new_status,
            changed_by=changed_by,
            notes=notes
        )

        history_repo = MissingPersonStatusHistoryRepository()
        history_repo.create(history)

        return self.update(missing_person)