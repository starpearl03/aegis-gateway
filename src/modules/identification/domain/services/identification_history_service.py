# ===== src/modules/identification/application/services/identification_search_service.py =====
import os
import logging
from typing import List, Dict, Any
from datetime import datetime

from src.modules.identification.domain.models.identification_search import IdentificationSearch
from src.modules.identification.domain.models.identification_result import IdentificationResult
from src.modules.identification.domain.models.enums import SearchType, FileType, SearchStatus, PersonType
from src.modules.identification.domain.repositories.identification_search_repository import \
    IdentificationSearchRepository
from src.modules.identification.domain.repositories.identification_result_repository import \
    IdentificationResultRepository
from src.modules.identification.application.dtos.identification_dtos import (
    CreateIdentificationSearchRequest,
    IdentificationSearchResponse,
    GetSearchResultsResponse
)
from src.modules.records.domain.repositories.person_repository import PersonRepository
from src.modules.records.domain.repositories.person_image_repository import PersonImageRepository
from src.modules.records.domain.repositories.criminal_repository import CriminalRepository
from src.modules.records.domain.repositories.missing_person_repository import MissingPersonRepository
from src.shared.configs.exceptions.exceptions import (
    NotFoundException,
    ValidationException,
    InternalServerException
)
from src.shared.utils.facial_recognition.facial_recognition_service import FacialRecognitionService

logger = logging.getLogger(__name__)


class IdentificationSearchService:
    """Service for performing facial recognition identification searches."""

    # Similarity threshold for matches (adjust based on testing)
    SIMILARITY_THRESHOLD = 0.35

    def __init__(self):
        self.search_repo = IdentificationSearchRepository()
        self.result_repo = IdentificationResultRepository()
        self.person_repo = PersonRepository()
        self.image_repo = PersonImageRepository()
        self.criminal_repo = CriminalRepository()
        self.missing_person_repo = MissingPersonRepository()
        self.facial_service = FacialRecognitionService()

    def create_and_process_search(self, request: CreateIdentificationSearchRequest) -> IdentificationSearchResponse:
        """
        Create a new identification search and process it immediately.

        Args:
            request: CreateIdentificationSearchRequest DTO

        Returns:
            IdentificationSearchResponse DTO

        Raises:
            ValidationException: If data is invalid
            NotFoundException: If file not found
            InternalServerException: If processing fails
        """
        # Verify file exists
        if not os.path.exists(request.file_path):
            raise NotFoundException(f"File not found: {request.file_path}")

        try:
            # Create search record
            search_type = self._get_enum_by_value(SearchType, request.search_type)
            file_type = self._get_enum_by_value(FileType, request.file_type)

            search = IdentificationSearch(
                search_type=search_type,
                file_path=request.file_path,
                file_type=file_type,
                status=SearchStatus.PENDING
            )

            saved_search = self.search_repo.create(search)
            logger.info(f"Created identification search: {saved_search.id}")

            # Process the search asynchronously (or immediately for now)
            self._process_search(saved_search.id)

            # Return the search response
            return self._build_search_response(saved_search)

        except Exception as e:
            logger.error(f"Failed to create identification search: {str(e)}", exc_info=True)
            raise InternalServerException(f"Failed to create identification search: {str(e)}")

    def _process_search(self, search_id: str) -> None:
        """
        Process an identification search by extracting face vectors and comparing against database.

        Args:
            search_id: ID of the search to process
        """
        try:
            # Get search record
            search = self.search_repo.find_by_id(search_id)
            if not search:
                raise NotFoundException(f"Search with ID {search_id} not found")

            # Update status to processing
            search.status = SearchStatus.PROCESSING
            self.search_repo.update(search)
            logger.info(f"Processing search {search_id}: {search.file_type.value} - {search.search_type.value}")

            # Extract face vectors from uploaded file
            face_vectors = self.facial_service.extract_face_vectors_from_file(
                search.file_path,
                search.file_type.value
            )

            if not face_vectors:
                logger.warning(f"No faces detected in file: {search.file_path}")
                search.status = SearchStatus.COMPLETED
                self.search_repo.update(search)
                return

            logger.info(f"Extracted {len(face_vectors)} face vectors from {search.file_type.value}")

            # Get target database based on search type
            if search.search_type == SearchType.CRIMINAL:
                target_persons = self.criminal_repo.find_all()
                person_type = PersonType.CRIMINAL
            else:  # MISSING_PERSON
                target_persons = self.missing_person_repo.find_all()
                person_type = PersonType.MISSING_PERSON

            logger.info(f"Comparing against {len(target_persons)} {person_type.value} records")

            # Compare each extracted face vector against all person images in database
            all_results = []
            for face_vector in face_vectors:
                results = self._compare_face_against_database(
                    face_vector,
                    target_persons,
                    person_type,
                    search_id
                )
                all_results.extend(results)

            # Save all results to database
            if all_results:
                self.result_repo.create_many(all_results)
                logger.info(f"Saved {len(all_results)} identification results for search {search_id}")

            # Update search status to completed
            search.status = SearchStatus.COMPLETED
            self.search_repo.update(search)
            logger.info(f"Search {search_id} completed successfully")

        except Exception as e:
            logger.error(f"Error processing search {search_id}: {str(e)}", exc_info=True)
            # Update search status to failed
            try:
                search = self.search_repo.find_by_id(search_id)
                if search:
                    search.status = SearchStatus.FAILED
                    self.search_repo.update(search)
            except Exception as update_error:
                logger.error(f"Failed to update search status: {str(update_error)}")

    def _compare_face_against_database(
            self,
            face_vector: List[float],
            target_persons: List,
            person_type: PersonType,
            search_id: str
    ) -> List[IdentificationResult]:
        """
        Compare a single face vector against all persons in database.

        Args:
            face_vector: Face embedding vector to compare
            target_persons: List of person entities to compare against
            person_type: Type of persons (criminal or missing_person)
            search_id: ID of the search

        Returns:
            List of IdentificationResult entities
        """
        results = []

        for person in target_persons:
            # Get all images for this person
            person_images = self.image_repo.find_by_person(person.id)

            for person_image in person_images:
                # Skip images without vectors
                if person_image.image_vector is None:
                    continue

                try:
                    # Calculate similarity
                    similarity_score = self.facial_service.calculate_similarity(
                        face_vector,
                        person_image.image_vector
                    )

                    # Create result for this comparison
                    is_match = similarity_score >= self.SIMILARITY_THRESHOLD

                    result = IdentificationResult(
                        search_id=search_id,
                        person_id=person.id,
                        person_type=person_type,
                        similarity_score=similarity_score,
                        is_match=is_match,
                        matched_image_id=person_image.id
                    )

                    results.append(result)

                    if is_match:
                        logger.info(
                            f"Match found! Person: {person.first_name} {person.last_name}, "
                            f"Score: {similarity_score:.4f}"
                        )

                except Exception as e:
                    logger.warning(f"Error comparing with image {person_image.id}: {str(e)}")
                    continue

        return results

    def get_search_results(self, search_id: str, matches_only: bool = True) -> GetSearchResultsResponse:
        """
        Get results for a specific search, grouped by person.

        Args:
            search_id: ID of the search
            matches_only: If True, only return matches above threshold

        Returns:
            GetSearchResultsResponse DTO

        Raises:
            NotFoundException: If search not found
        """
        search = self.search_repo.find_by_id(search_id)
        if not search:
            raise NotFoundException(f"Search with ID {search_id} not found")

        # Get best match per person
        if matches_only:
            results = self.result_repo.get_best_match_per_person(search_id)
        else:
            results = self.result_repo.find_by_search(search_id)

        # Group results by person and build response
        grouped_results = []
        for result in results:
            person_details = self._get_person_details(result.person_id, result.person_type)
            matched_image_path = None

            if result.matched_image_id:
                matched_image = self.image_repo.find_by_id(result.matched_image_id)
                if matched_image:
                    matched_image_path = matched_image.image_path

            grouped_results.append({
                'result_id': result.id,
                'person_id': result.person_id,
                'person_type': result.person_type.value if result.person_type else None,
                'similarity_score': result.similarity_score,
                'is_match': result.is_match,
                'matched_image_id': result.matched_image_id,
                'matched_image_path': matched_image_path,
                'person_details': person_details
            })

        # Sort by similarity score descending
        grouped_results.sort(key=lambda x: x['similarity_score'], reverse=True)

        total_matches = len([r for r in results if r.is_match])

        return GetSearchResultsResponse(
            message=f"Found {total_matches} match(es)" if matches_only else f"Found {len(results)} result(s)",
            search_id=search.id,
            search_type=search.search_type.value,
            file_path=search.file_path,
            status=search.status.value,
            total_matches=total_matches,
            unique_persons=len(grouped_results),
            grouped_results=grouped_results,
            created_at=search.created_at.isoformat()
        )

    def _get_person_details(self, person_id: str, person_type: PersonType) -> Dict[str, Any]:
        """
        Get person details based on person type.

        Args:
            person_id: ID of the person
            person_type: Type of person (criminal or missing_person)

        Returns:
            Dictionary with person details
        """
        try:
            if person_type == PersonType.CRIMINAL:
                criminal = self.criminal_repo.find_by_id(person_id)
                if not criminal:
                    return {}

                return {
                    'id': criminal.id,
                    'first_name': criminal.first_name,
                    'last_name': criminal.last_name,
                    'alias': criminal.alias,
                    'is_wanted': criminal.is_wanted,
                    'priority_level': criminal.priority_level,
                    'threat_level': criminal.threat_level.value if criminal.threat_level else None,
                    'national_id': criminal.national_id,
                    'distinctive_features': criminal.distinctive_features
                }
            else:  # MISSING_PERSON
                missing_person = self.missing_person_repo.find_by_id(person_id)
                if not missing_person:
                    return {}

                return {
                    'id': missing_person.id,
                    'first_name': missing_person.first_name,
                    'last_name': missing_person.last_name,
                    'status': missing_person.status.value,
                    'last_seen_date': missing_person.last_seen_date.isoformat() if missing_person.last_seen_date else None,
                    'national_id': missing_person.national_id,
                    'distinctive_features': missing_person.distinctive_features
                }
        except Exception as e:
            logger.error(f"Error getting person details: {str(e)}")
            return {}

    def _build_search_response(self, search: IdentificationSearch) -> IdentificationSearchResponse:
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
    def _get_enum_by_value(enum_class, value: str):
        """Get enum member by its value (case-insensitive)."""
        if not value:
            raise ValidationException(f"Value cannot be empty for {enum_class.__name__}")

        value_lower = value.lower().strip()
        for member in enum_class:
            if member.value.lower() == value_lower:
                return member

        valid_values = [member.value for member in enum_class]
        raise ValidationException(
            f"Invalid {enum_class.__name__} value: '{value}'. "
            f"Valid options are: {', '.join(valid_values)}"
        )


# ===== src/modules/identification/application/services/identification_history_service.py =====
import logging
from typing import List

from src.modules.identification.domain.repositories.identification_search_repository import \
    IdentificationSearchRepository
from src.modules.identification.domain.repositories.identification_result_repository import \
    IdentificationResultRepository
from src.modules.identification.domain.models.enums import SearchStatus
from src.modules.identification.application.dtos.identification_dtos import (
    ListIdentificationSearchesRequest,
    ListIdentificationSearchesResponse,
    IdentificationSearchResponse,
    IdentificationDeleteResponse
)
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
            all_searches = self.search_repo.find_by_search_type(
                self._get_enum_by_value_safe(request.search_type)
            )
            status_enum = self._get_enum_by_value_safe_status(request.status)
            searches = [s for s in all_searches if s.status == status_enum]
        elif request.search_type:
            searches = self.search_repo.find_by_search_type(
                self._get_enum_by_value_safe(request.search_type)
            )
        elif request.status:
            searches = self.search_repo.find_by_status(
                self._get_enum_by_value_safe_status(request.status)
            )
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

    def _get_enum_by_value_safe(self, value: str):
        """Safely get SearchType enum by value."""
        from src.modules.identification.domain.models.enums import SearchType
        value_lower = value.lower().strip()
        for member in SearchType:
            if member.value.lower() == value_lower:
                return member
        return None

    def _get_enum_by_value_safe_status(self, value: str):
        """Safely get SearchStatus enum by value."""
        value_lower = value.lower().strip()
        for member in SearchStatus:
            if member.value.lower() == value_lower:
                return member
        return None