# ===== shared/utils/statistics_utils.py =====
from datetime import datetime

from src.modules.records.domain.models.enums import CrimeStatus
from src.modules.records.domain.repositories.crime_repository import CrimeRepository
from src.modules.records.domain.repositories.criminal_repository import CriminalRepository
from src.modules.records.domain.repositories.missing_person_repository import MissingPersonRepository
from src.modules.records.domain.repositories.punishment_repository import PunishmentRepository
from src.modules.records.presentation.dtos.record_management import GetStatisticsRequest, StatisticsResponse


class StatisticsUtils:
    """Utility class for generating system statistics."""

    def __init__(self):
        self.missing_person_repo = MissingPersonRepository()
        self.criminal_repo = CriminalRepository()
        self.crime_repo = CrimeRepository()
        self.punishment_repo = PunishmentRepository()

    def get_dashboard_statistics(self, request: GetStatisticsRequest) -> StatisticsResponse:
        """
        Get dashboard statistics.

        Args:
            request: GetStatisticsRequest DTO with optional filters

        Returns:
            StatisticsResponse DTO
        """
        # Missing persons statistics
        total_missing = self.missing_person_repo.count()
        active_missing = len(self.missing_person_repo.find_active_cases())

        # Criminal statistics
        total_criminals = self.criminal_repo.count()
        wanted_criminals = len(self.criminal_repo.find_wanted())

        # Crime statistics
        total_crimes = self.crime_repo.count()
        open_crimes = len(self.crime_repo.find_open_cases())

        # Calculate solved crimes (crimes with status CLOSED_UNSOLVED or SOLVED)
        all_crimes = self.crime_repo.find_all()
        solved_crimes = sum(
            1 for crime in all_crimes
            if crime.status in [CrimeStatus.CLOSED_UNSOLVED, CrimeStatus.SOLVED]
        )

        # Punishment statistics
        total_punishments = self.punishment_repo.count()
        active_punishments = len(self.punishment_repo.find_active_punishments())

        # Filter by officer if specified
        if request.officer_id:
            # Get officer-specific statistics
            officer_missing = len(
                self.missing_person_repo.find_by_officer(request.officer_id)
            )
            officer_crimes = len(
                self.crime_repo.find_by_officer(request.officer_id)
            )

            # Override totals with officer-specific counts
            total_missing = officer_missing
            total_crimes = officer_crimes

        # Filter by date range if specified
        if request.start_date and request.end_date:
            start = datetime.fromisoformat(request.start_date)
            end = datetime.fromisoformat(request.end_date)

            # Get date-filtered counts
            date_filtered_missing = self.missing_person_repo.find_by_date_range(start, end)
            date_filtered_crimes = self.crime_repo.find_by_date_range(start, end)

            total_missing = len(date_filtered_missing)
            total_crimes = len(date_filtered_crimes)

        return StatisticsResponse(
            message="Statistics retrieved successfully",
            total_missing_persons=total_missing,
            active_missing_cases=active_missing,
            total_criminals=total_criminals,
            wanted_criminals=wanted_criminals,
            total_crimes=total_crimes,
            open_crimes=open_crimes,
            solved_crimes=solved_crimes,
            total_punishments=total_punishments,
            active_punishments=active_punishments
        )

    def get_officer_statistics(self, officer_id: str) -> StatisticsResponse:
        """
        Get statistics for a specific officer.

        Args:
            officer_id: User ID of the officer

        Returns:
            StatisticsResponse DTO
        """
        request = GetStatisticsRequest(officer_id=officer_id)
        return self.get_dashboard_statistics(request)

    def get_statistics_by_date_range(
            self,
            start_date: str,
            end_date: str
    ) -> StatisticsResponse:
        """
        Get statistics for a specific date range.

        Args:
            start_date: Start date in ISO format
            end_date: End date in ISO format

        Returns:
            StatisticsResponse DTO
        """
        request = GetStatisticsRequest(
            start_date=start_date,
            end_date=end_date
        )
        return self.get_dashboard_statistics(request)