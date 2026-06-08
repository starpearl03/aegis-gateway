# ===== criminal/repositories/crime_repository.py =====
from datetime import datetime
from typing import List, Optional

from src.modules.records.domain.models.crime import Crime
from src.modules.records.domain.models.enums import CrimeStatus
from src.shared.data.base.repository import BaseRepository


class CrimeRepository(BaseRepository[Crime]):
    """Repository for Crime model"""

    def __init__(self):
        super().__init__(Crime)

    def find_by_case_number(self, case_number: str) -> Optional[Crime]:
        """Find crime by case number"""
        return self.find_one_by({"case_number": case_number})

    def find_by_status(self, status: CrimeStatus) -> List[Crime]:
        """Find all crimes by status"""
        return self.find_many_by({"status": status})

    def find_open_cases(self) -> List[Crime]:
        """Find all open crime cases"""
        return self.find_by_status(CrimeStatus.OPEN)

    def find_by_criminal(self, criminal_id: str) -> List[Crime]:
        """Find all crimes committed by a specific criminal"""
        return self.find_many_by({"criminal_id": criminal_id})

    def find_by_crime_type(self, crime_type: str) -> List[Crime]:
        """Find all crimes of a specific type"""
        return self.find_many_by({"crime_type": crime_type})

    def find_by_officer(self, officer_id: str) -> List[Crime]:
        """Find all crimes assigned to a specific officer"""
        return self.find_many_by({"assigned_officer_id": officer_id})

    def find_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Crime]:
        """
        Find crimes committed within a date range.

        Args:
            start_date: Start date of the range
            end_date: End date of the range

        Returns:
            List of crimes committed in the date range
        """
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.date_committed.between(start_date, end_date)
        ).all()

    def find_by_location(self, location_id: str) -> List[Crime]:
        """Find crimes that occurred at a specific location"""
        return self.find_many_by({"location_id": location_id})

    def find_recent_crimes(self, days: int = 30) -> List[Crime]:
        """
        Find crimes reported within the last N days.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            List of recent crimes
        """
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)

        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.date_reported >= cutoff_date
        ).order_by(self.model.date_reported.desc()).all()

    def find_unassigned_cases(self) -> List[Crime]:
        """Find all crimes without an assigned officer"""
        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.assigned_officer_id.is_(None)
        ).all()