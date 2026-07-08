# ===== src/modules/identification/application/services/identification_search_service.py =====
import os
import logging
from typing import List, Dict, Any

from src.modules.identification.domain.models import SearchType, FileType, IdentificationSearch, SearchStatus, \
    PersonType, IdentificationResult
from src.modules.identification.domain.repositories.dentification_search_repository import \
    IdentificationSearchRepository
from src.modules.identification.domain.repositories.identification_result_repository import \
    IdentificationResultRepository
from src.modules.identification.presentation.dtos.identification_dtos import CreateIdentificationSearchRequest, \
    IdentificationSearchResponse, GetSearchResultsResponse
from src.modules.records.domain.repositories.criminal_repository import CriminalRepository
from src.modules.records.domain.repositories.missing_person_repository import MissingPersonRepository
from src.modules.records.domain.repositories.person_image_repository import PersonImageRepository
from src.modules.records.domain.repositories.person_repository import PersonRepository
from src.modules.records.domain.repositories.reporter_repository import ReporterRepository
from src.shared.configs.exceptions.exceptions import NotFoundException, InternalServerException, ValidationException
from src.shared.utils.facial_recongition_service import FacialRecognitionService

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
        self.reporter_repo = ReporterRepository()
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

            # Process the search immediately
            self._process_search(saved_search.id)

            # Reload search to get updated status
            saved_search = self.search_repo.find_by_id(saved_search.id)

            # Return the search response
            return self._build_search_response(saved_search)

        except Exception as e:
            logger.error(f"Failed to create identification search: {str(e)}", exc_info=True)
            raise InternalServerException(f"Failed to create identification search: {str(e)}")

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

            # Build result with enhanced person details
            result_dict = {
                'result_id': result.id,
                'person_id': result.person_id,
                'person_type': result.person_type.value if result.person_type else None,
                'similarity_score': result.similarity_score,
                'is_match': result.is_match,
                'matched_image_id': result.matched_image_id,
                'matched_image_path': matched_image_path,
                'person_details': person_details,
                # Add flag for missing person (controller will handle notification logic)
                'is_missing_person': result.person_type == PersonType.MISSING_PERSON
            }

            grouped_results.append(result_dict)

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
            person_images = self.image_repo.find_by_person_id(person.id)

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

                    # Convert numpy float64 to Python float for PostgreSQL compatibility
                    similarity_score = float(similarity_score)

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

                # Get primary image
                primary_image = None
                primary_image_obj = criminal.images.filter_by(is_primary=True).first()
                if primary_image_obj:
                    primary_image = primary_image_obj.image_path

                return {
                    'id': criminal.id,
                    'first_name': criminal.first_name,
                    'last_name': criminal.last_name,
                    'full_name': f"{criminal.first_name} {criminal.last_name}",
                    'alias': criminal.alias,
                    'is_wanted': criminal.is_wanted,
                    'priority_level': criminal.priority_level,
                    'threat_level': criminal.threat_level.value if criminal.threat_level else None,
                    'national_id': criminal.national_id,
                    'distinctive_features': criminal.distinctive_features,
                    'primary_image': primary_image,
                    'gender': criminal.gender.value if criminal.gender else None,
                    'date_of_birth': criminal.date_of_birth.isoformat() if criminal.date_of_birth else None
                }
            else:  # MISSING_PERSON
                missing_person = self.missing_person_repo.find_by_id(person_id)
                if not missing_person:
                    return {}

                # Get primary image
                primary_image = None
                primary_image_obj = missing_person.images.filter_by(is_primary=True).first()
                if primary_image_obj:
                    primary_image = primary_image_obj.image_path

                # Get reporter info
                reporter = self.reporter_repo.find_by_missing_person(person_id)
                reporter_info = None
                if reporter:
                    reporter_info = {
                        'name': f"{reporter.first_name} {reporter.last_name}",
                        'phone': reporter.phone_number,
                        'email': reporter.email,
                        'relationship': reporter.relationship.value if reporter.relationship else None
                    }

                return {
                    'id': missing_person.id,
                    'first_name': missing_person.first_name,
                    'last_name': missing_person.last_name,
                    'full_name': f"{missing_person.first_name} {missing_person.last_name}",
                    'status': missing_person.status.value,
                    'last_seen_date': missing_person.last_seen_date.isoformat() if missing_person.last_seen_date else None,
                    'national_id': missing_person.national_id,
                    'distinctive_features': missing_person.distinctive_features,
                    'primary_image': primary_image,
                    'gender': missing_person.gender.value if missing_person.gender else None,
                    'date_of_birth': missing_person.date_of_birth.isoformat() if missing_person.date_of_birth else None,
                    'reporter': reporter_info
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
