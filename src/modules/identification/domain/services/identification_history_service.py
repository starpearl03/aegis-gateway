# ===== src/modules/identification/application/services/identification_history_service.py =====
import logging
from typing import List

from src.modules.identification.domain.models import SearchType, SearchStatus
from src.modules.identification.domain.repositories.dentification_search_repository import \
    IdentificationSearchRepository
from src.modules.identification.domain.repositories.identification_result_repository import \
    IdentificationResultRepository
from src.modules.identification.presentation.dtos.identification_dtos import ListIdentificationSearchesRequest, \
    ListIdentificationSearchesResponse, IdentificationSearchResponse, IdentificationDeleteResponse
from src.shared.configs.exceptions.exceptions import NotFoundException

logger = logging.getLogger(__name__)


class IdentificationHistoryService:
    """Service for managing identification search history."""

    def __init__(self):
        self.search_repo = IdentificationSearchRepository()
        self.result_repo = IdentificationResultRepository()

    def list_searches(self, request: ListIdentificationSearchesRequest) -> ListIdentificationSearchesResponse:
        """
        List identification searches with filters and pagination.

        Args:
            request: ListIdentificationSearchesRequest DTO

        Returns:
            ListIdentificationSearchesResponse DTO
        """
        # Build query based on filters
        if request.search_type and request.status:
            # Filter by both
            search_type_enum = self._get_enum_by_value_safe(SearchType, request.search_type)
            status_enum = self._get_enum_by_value_safe(SearchStatus, request.status)

            if search_type_enum:
                all_searches = self.search_repo.find_by_search_type(search_type_enum)
                searches = [s for s in all_searches if s.status == status_enum] if status_enum else all_searches
            else:
                searches = []
        elif request.search_type:
            search_type_enum = self._get_enum_by_value_safe(SearchType, request.search_type)
            searches = self.search_repo.find_by_search_type(search_type_enum) if search_type_enum else []
        elif request.status:
            status_enum = self._get_enum_by_value_safe(SearchStatus, request.status)
            searches = self.search_repo.find_by_status(status_enum) if status_enum else []
        else:
            searches = self.search_repo.find_all(include_deleted=request.include_deleted)

        # Sort by created_at descending (most recent first)
        searches.sort(key=lambda x: x.created_at, reverse=True)

        # Pagination
        total = len(searches)
        start = (request.page - 1) * request.per_page
        end = start + request.per_page
        paginated_searches = searches[start:end]

        # Build response with match counts
        search_dicts = []
        for search in paginated_searches:
            search_dict = self._build_search_response(search).to_dict()

            # Add match count
            match_count = self.result_repo.count_matches_by_search(search.id)
            search_dict['match_count'] = match_count

            search_dicts.append(search_dict)

        return ListIdentificationSearchesResponse(
            message=f"Found {total} search(es)",
            searches=search_dicts,
            total=total,
            page=request.page,
            per_page=request.per_page,
            total_pages=(total + request.per_page - 1) // request.per_page
        )

    def get_search_by_id(self, search_id: str) -> IdentificationSearchResponse:
        """
        Get a specific search by ID.

        Args:
            search_id: ID of the search

        Returns:
            IdentificationSearchResponse DTO

        Raises:
            NotFoundException: If search not found
        """
        search = self.search_repo.find_by_id(search_id)
        if not search:
            raise NotFoundException(f"Search with ID {search_id} not found")

        return self._build_search_response(search)

    def get_recent_searches(self, days: int = 7) -> List[IdentificationSearchResponse]:
        """
        Get recent searches within the last N days.

        Args:
            days: Number of days to look back (default: 7)

        Returns:
            List of IdentificationSearchResponse DTOs
        """
        searches = self.search_repo.find_recent_searches(days=days)
        return [self._build_search_response(search) for search in searches]

    def get_pending_searches(self) -> List[IdentificationSearchResponse]:
        """
        Get all pending searches.

        Returns:
            List of IdentificationSearchResponse DTOs
        """
        searches = self.search_repo.find_pending_searches()
        return [self._build_search_response(search) for search in searches]

    def get_completed_searches(self) -> List[IdentificationSearchResponse]:
        """
        Get all completed searches.

        Returns:
            List of IdentificationSearchResponse DTOs
        """
        searches = self.search_repo.find_completed_searches()
        return [self._build_search_response(search) for search in searches]

    def delete_search(self, search_id: str) -> IdentificationDeleteResponse:
        """
        Soft delete a search and its results.

        Args:
            search_id: ID of the search

        Returns:
            IdentificationDeleteResponse DTO

        Raises:
            NotFoundException: If search not found
        """
        search = self.search_repo.find_by_id(search_id)
        if not search:
            raise NotFoundException(f"Search with ID {search_id} not found")

        # Delete associated results
        results = self.result_repo.find_by_search(search_id)
        if results:
            self.result_repo.delete_many(results)
            logger.info(f"Deleted {len(results)} results for search {search_id}")

        # Delete search
        self.search_repo.delete(search)
        logger.info(f"Deleted search {search_id}")

        return IdentificationDeleteResponse(
            message="Search deleted successfully",
            id=search_id
        )

    def get_search_statistics(self) -> dict:
        """
        Get statistics about identification searches.

        Returns:
            Dictionary with statistics
        """
        total_searches = self.search_repo.count()
        pending = len(self.search_repo.find_pending_searches())
        completed = len(self.search_repo.find_completed_searches())
        failed = len(self.search_repo.find_failed_searches())

        # Get total matches across all searches
        total_matches = sum(
            self.result_repo.count_matches_by_search(search.id)
            for search in self.search_repo.find_all()
        )

        return {
            'total_searches': total_searches,
            'pending_searches': pending,
            'completed_searches': completed,
            'failed_searches': failed,
            'total_matches_found': total_matches
        }

    def _build_search_response(self, search) -> IdentificationSearchResponse:
        """Build IdentificationSearchResponse DTO from entity."""
        return IdentificationSearchResponse(
            id=search.id,
            search_type=search.search_type.value,
            file_path=search.file_path,
            file_type=search.file_type.value,
            status=search.status.value,
            created_at=search.created_at.isoformat(),
            updated_at=search.updated_at.isoformat()
        )

    @staticmethod
    def _get_enum_by_value_safe(enum_class, value: str):
        """Safely get enum by value, returns None if not found."""
        if not value:
            return None

        value_lower = value.lower().strip()
        for member in enum_class:
            if member.value.lower() == value_lower:
                return member
        return None
