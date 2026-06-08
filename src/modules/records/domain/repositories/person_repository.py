# ===== shared/repositories/person_repository.py =====
from datetime import date
from typing import List, Optional
from sqlalchemy import or_, func

from src.modules.records.domain.models.person import Person
from src.shared.data.base.repository import BaseRepository


class PersonRepository(BaseRepository[Person]):
    """Repository for Person model"""

    def __init__(self):
        super().__init__(Person)

    def find_by_national_id(self, national_id: str) -> Optional[Person]:
        """Find person by national ID"""
        return self.find_one_by({"national_id": national_id})

    def find_by_name(self, first_name: str, last_name: str) -> List[Person]:
        """Find persons by first and last name"""
        return self.find_many_by({"first_name": first_name, "last_name": last_name})

    def search_by_name(self, name: str) -> List[Person]:
        """
        Search persons by partial name match (first or last name).

        Args:
            name: Name to search for (case-insensitive)

        Returns:
            List of persons matching the search
        """
        search_pattern = f"%{name.lower()}%"
        return self.model.query.filter(
            self.model.is_deleted == False,
            or_(
                func.lower(self.model.first_name).like(search_pattern),
                func.lower(self.model.last_name).like(search_pattern)
            )
        ).all()

    def find_by_phone(self, phone_number: str) -> List[Person]:
        """Find persons by phone number"""
        return self.find_many_by({"phone_number": phone_number})

    def find_by_email(self, email: str) -> Optional[Person]:
        """Find person by email"""
        return self.find_one_by({"email": email})

    def find_by_age_range(self, min_age: int, max_age: int) -> List[Person]:
        """
        Find persons within an age range.

        Args:
            min_age: Minimum age
            max_age: Maximum age

        Returns:
            List of persons within the age range
        """
        from datetime import datetime, timedelta
        today = date.today()
        max_birth_date = today - timedelta(days=min_age * 365)
        min_birth_date = today - timedelta(days=(max_age + 1) * 365)

        return self.model.query.filter(
            self.model.is_deleted == False,
            self.model.date_of_birth.between(min_birth_date, max_birth_date)
        ).all()