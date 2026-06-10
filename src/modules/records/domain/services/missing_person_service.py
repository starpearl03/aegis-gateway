# ===== missing_person/services/missing_person_service.py =====
from typing import List, Dict, Any
from datetime import datetime

from src.modules.records.domain.models.enums import MissingPersonStatus
from src.modules.records.domain.models.missing_person import MissingPerson
from src.modules.records.domain.models.reporter import Reporter
from src.modules.records.domain.repositories.missing_person_repository import MissingPersonRepository
from src.modules.records.domain.repositories.missing_person_status_history_repository import \
    MissingPersonStatusHistoryRepository
from src.modules.records.domain.repositories.person_repository import PersonRepository
from src.modules.records.domain.repositories.reporter_repository import ReporterRepository
from src.modules.records.internal.location_utils import LocationUtils
from src.modules.records.internal.person_image_utils import PersonImageUtils
from src.modules.records.presentation.dtos.record_management import CreateMissingPersonRequest, MissingPersonResponse, \
    UpdateMissingPersonRequest, UpdateMissingPersonStatusRequest, ListMissingPersonsRequest, ListMissingPersonsResponse, \
    SearchPersonRequest, SearchPersonResponse, DeleteResponse, CreatePersonImageRequest, PersonImageResponse
from src.shared.configs.exceptions.exceptions import AlreadyExistsException, NotFoundException, ValidationException


class MissingPersonService:
    """Service for managing missing person records."""

    def __init__(self):
        self.missing_person_repo = MissingPersonRepository()
        self.reporter_repo = ReporterRepository()
        self.person_repo = PersonRepository()
        self.status_history_repo = MissingPersonStatusHistoryRepository()
        self.location_utils = LocationUtils()
        self.image_utils = PersonImageUtils()

    def report_missing_person(self, request: CreateMissingPersonRequest) -> MissingPersonResponse:
        """
        Report a new missing person.

        Args:
            request: CreateMissingPersonRequest DTO

        Returns:
            MissingPersonResponse DTO

        Raises:
            ValidationException: If data is invalid
            AlreadyExistsException: If person with same national_id exists
        """
        # Check if person with same national_id already exists in missing persons
        if request.national_id:
            existing_person = self.person_repo.find_by_national_id(request.national_id)
            if existing_person and existing_person.type == 'missing_person':
                raise AlreadyExistsException(
                    f"Missing person with national ID {request.national_id} already exists"
                )

        try:
            # Verify location exists
            self.location_utils.get_location_by_id(request.last_seen_location_id)

            # Create missing person entity
            missing_person = MissingPerson(
                first_name=request.first_name,
                last_name=request.last_name,
                date_of_birth=datetime.fromisoformat(request.date_of_birth).date() if request.date_of_birth else None,
                gender=request.gender,
                phone_number=request.phone_number,
                email=request.email,
                national_id=request.national_id,
                height=request.height,
                weight=request.weight,
                hair_color=request.hair_color,
                eye_color=request.eye_color,
                skin_tone=request.skin_tone,
                distinctive_features=request.distinctive_features,
                description=request.description,
                last_seen_date=datetime.fromisoformat(request.last_seen_date),
                last_seen_location_id=request.last_seen_location_id,
                circumstances=request.circumstances,
                assigned_officer_id=request.assigned_officer_id,
                status=MissingPersonStatus.MISSING,
                created_by=request.created_by
            )

            # Save missing person
            saved_missing_person = self.missing_person_repo.create(missing_person)

            # Create reporter entity
            reporter = Reporter(
                first_name=request.reporter_first_name,
                last_name=request.reporter_last_name,
                relationship=request.reporter_relationship,
                phone_number=request.reporter_phone,
                email=request.reporter_email,
                address_id=request.reporter_address_id,
                missing_person_id=saved_missing_person.id,
                recorded_by=request.created_by
            )

            # Save reporter
            self.reporter_repo.create(reporter)

            # Return response
            return self._build_missing_person_response(saved_missing_person)

        except NotFoundException:
            raise
        except Exception as e:
            raise ValidationException(f"Failed to report missing person: {str(e)}")

    def update_missing_person(self, request: UpdateMissingPersonRequest) -> MissingPersonResponse:
        """
        Update missing person details.

        Args:
            request: UpdateMissingPersonRequest DTO

        Returns:
            MissingPersonResponse DTO

        Raises:
            NotFoundException: If missing person not found
            ValidationException: If update data is invalid
        """
        # Find missing person
        missing_person = self.missing_person_repo.find_by_id(request.missing_person_id)
        if not missing_person:
            raise NotFoundException(
                f"Missing person with ID {request.missing_person_id} not found"
            )

        try:
            # Update fields if provided
            if request.status is not None:
                missing_person.status = MissingPersonStatus[request.status]

            if request.circumstances is not None:
                missing_person.circumstances = request.circumstances

            if request.found_date is not None:
                missing_person.found_date = datetime.fromisoformat(request.found_date)

            if request.found_location_id is not None:
                # Verify location exists
                self.location_utils.get_location_by_id(request.found_location_id)
                missing_person.found_location_id = request.found_location_id

            if request.found_condition is not None:
                missing_person.found_condition = request.found_condition

            if request.assigned_officer_id is not None:
                missing_person.assigned_officer_id = request.assigned_officer_id

            if request.updated_by is not None:
                missing_person.updated_by = request.updated_by

            # Save updates
            updated_missing_person = self.missing_person_repo.update(missing_person)

            return self._build_missing_person_response(updated_missing_person)

        except NotFoundException:
            raise
        except Exception as e:
            raise ValidationException(f"Failed to update missing person: {str(e)}")

    def update_missing_person_status(
            self,
            request: UpdateMissingPersonStatusRequest
    ) -> MissingPersonResponse:
        """
        Update missing person status with history tracking.

        Args:
            request: UpdateMissingPersonStatusRequest DTO

        Returns:
            MissingPersonResponse DTO

        Raises:
            NotFoundException: If missing person not found
            ValidationException: If status is invalid
        """
        try:
            # Validate status
            try:
                new_status = MissingPersonStatus[request.new_status]
            except KeyError:
                raise ValidationException(f"Invalid status: {request.new_status}")

            # Update status using repository method (creates history automatically)
            updated_missing_person = self.missing_person_repo.update_status(
                missing_person_id=request.missing_person_id,
                new_status=new_status,
                changed_by=request.changed_by,
                notes=request.notes
            )

            return self._build_missing_person_response(updated_missing_person)

        except NotFoundException:
            raise
        except Exception as e:
            raise ValidationException(f"Failed to update status: {str(e)}")

    def get_missing_person_by_id(self, missing_person_id: str) -> MissingPersonResponse:
        """
        Get missing person by ID.

        Args:
            missing_person_id: Missing person ID

        Returns:
            MissingPersonResponse DTO

        Raises:
            NotFoundException: If missing person not found
        """
        missing_person = self.missing_person_repo.find_by_id(missing_person_id)

        if not missing_person:
            raise NotFoundException(
                f"Missing person with ID {missing_person_id} not found"
            )

        return self._build_missing_person_response(missing_person)

    def list_missing_persons(self, request: ListMissingPersonsRequest) -> ListMissingPersonsResponse:
        """
        List missing persons with filters and pagination.

        Args:
            request: ListMissingPersonsRequest DTO

        Returns:
            ListMissingPersonsResponse DTO
        """
        # Build query based on filters
        if request.status:
            try:
                status = MissingPersonStatus[request.status]
                missing_persons = self.missing_person_repo.find_by_status(status)
            except KeyError:
                raise ValidationException(f"Invalid status: {request.status}")
        elif request.assigned_officer_id:
            missing_persons = self.missing_person_repo.find_by_officer(
                request.assigned_officer_id
            )
        else:
            missing_persons = self.missing_person_repo.find_all(
                include_deleted=request.include_deleted
            )

        # Pagination
        total = len(missing_persons)
        start = (request.page - 1) * request.per_page
        end = start + request.per_page
        paginated_persons = missing_persons[start:end]

        # Convert to dict
        person_dicts = [
            self._build_missing_person_response(person).to_dict()
            for person in paginated_persons
        ]

        return ListMissingPersonsResponse(
            message=f"Found {total} missing person(s)",
            missing_persons=person_dicts,
            total=total,
            page=request.page,
            per_page=request.per_page,
            total_pages=(total + request.per_page - 1) // request.per_page
        )

    def get_active_cases(self) -> List[MissingPersonResponse]:
        """
        Get all active missing person cases.

        Returns:
            List of MissingPersonResponse DTOs
        """
        active_cases = self.missing_person_repo.find_active_cases()

        return [
            self._build_missing_person_response(person)
            for person in active_cases
        ]

    def get_cases_by_officer(self, officer_id: str) -> List[MissingPersonResponse]:
        """
        Get all cases assigned to an officer.

        Args:
            officer_id: Officer user ID

        Returns:
            List of MissingPersonResponse DTOs
        """
        cases = self.missing_person_repo.find_by_officer(officer_id)

        return [
            self._build_missing_person_response(person)
            for person in cases
        ]

    def delete_missing_person(self, missing_person_id: str) -> DeleteResponse:
        """
        Soft delete a missing person record.

        Args:
            missing_person_id: Missing person ID

        Returns:
            DeleteResponse DTO

        Raises:
            NotFoundException: If missing person not found
        """
        missing_person = self.missing_person_repo.find_by_id(missing_person_id)

        if not missing_person:
            raise NotFoundException(
                f"Missing person with ID {missing_person_id} not found"
            )

        self.missing_person_repo.delete(missing_person)

        return DeleteResponse(
            message="Missing person deleted successfully",
            id=missing_person_id
        )

    def search_missing_persons(self, request: SearchPersonRequest) -> SearchPersonResponse:
        """
        Search missing persons by various criteria.

        Args:
            request: SearchPersonRequest DTO

        Returns:
            SearchPersonResponse DTO
        """
        # Search based on search type
        if request.search_type == "name":
            persons = self.person_repo.search_by_name(request.query)
            # Filter only missing persons
            persons = [p for p in persons if p.type == 'missing_person']
        elif request.search_type == "phone":
            persons = self.person_repo.find_by_phone(request.query)
            persons = [p for p in persons if p.type == 'missing_person']
        elif request.search_type == "email":
            person = self.person_repo.find_by_email(request.query)
            persons = [person] if person and person.type == 'missing_person' else []
        elif request.search_type == "national_id":
            person = self.person_repo.find_by_national_id(request.query)
            persons = [person] if person and person.type == 'missing_person' else []
        else:
            raise ValidationException(f"Invalid search type: {request.search_type}")

        # Pagination
        total = len(persons)
        start = (request.page - 1) * request.per_page
        end = start + request.per_page
        paginated_persons = persons[start:end]

        # Convert to MissingPerson and build response
        results = [
            self._build_missing_person_response(
                self.missing_person_repo.find_by_id(person.id)
            ).to_dict()
            for person in paginated_persons
        ]

        return SearchPersonResponse(
            message=f"Found {total} result(s)",
            results=results,
            total=total,
            page=request.page,
            per_page=request.per_page,
            total_pages=(total + request.per_page - 1) // request.per_page
        )

    def upload_missing_person_image(
            self,
            missing_person_id: str,
            request: CreatePersonImageRequest
    ) -> PersonImageResponse:
        """
        Upload an image for a missing person.

        Args:
            missing_person_id: Missing person ID
            request: CreatePersonImageRequest DTO

        Returns:
            PersonImageResponse DTO

        Raises:
            NotFoundException: If missing person not found
        """
        # Verify missing person exists
        missing_person = self.missing_person_repo.find_by_id(missing_person_id)
        if not missing_person:
            raise NotFoundException(
                f"Missing person with ID {missing_person_id} not found"
            )

        # Set person_id to missing_person_id
        request.person_id = missing_person_id

        # Use image utils to upload
        return self.image_utils.upload_person_image(request)

    def get_missing_person_statistics(self) -> Dict[str, Any]:
        """
        Get statistics specific to missing persons.

        Returns:
            Dictionary with statistics
        """
        total = self.missing_person_repo.count()
        active = len(self.missing_person_repo.find_active_cases())
        found = len(self.missing_person_repo.find_by_status(MissingPersonStatus.LOCATED_ALIVE))
        deceased = len(self.missing_person_repo.find_by_status(MissingPersonStatus.LOCATED_DECEASED))

        return {
            'total_missing_persons': total,
            'active_cases': active,
            'found_alive': found,
            'found_deceased': deceased,
            'closed_investigations': total - active
        }

    def _build_missing_person_response(self, missing_person: MissingPerson) -> MissingPersonResponse:
        """
        Helper method to build MissingPersonResponse from entity.

        Args:
            missing_person: MissingPerson entity

        Returns:
            MissingPersonResponse DTO
        """
        # Get location details
        last_seen_location = None
        if missing_person.last_seen_location_id:
            try:
                loc = self.location_utils.get_location_by_id(
                    missing_person.last_seen_location_id
                )
                last_seen_location = loc.to_dict()
            except NotFoundException:
                pass

        found_location = None
        if missing_person.found_location_id:
            try:
                loc = self.location_utils.get_location_by_id(
                    missing_person.found_location_id
                )
                found_location = loc.to_dict()
            except NotFoundException:
                pass

        # Get reporter details
        reporter_dict = None
        reporter = self.reporter_repo.find_by_missing_person(missing_person.id)
        if reporter:
            reporter_dict = {
                'id': reporter.id,
                'first_name': reporter.first_name,
                'last_name': reporter.last_name,
                'relationship': reporter.relationship,
                'phone_number': reporter.phone_number,
                'email': reporter.email
            }

        return MissingPersonResponse(
            id=missing_person.id,
            first_name=missing_person.first_name,
            last_name=missing_person.last_name,
            date_of_birth=missing_person.date_of_birth.isoformat() if missing_person.date_of_birth else None,
            gender=missing_person.gender,
            phone_number=missing_person.phone_number,
            email=missing_person.email,
            height=missing_person.height,
            weight=missing_person.weight,
            hair_color=missing_person.hair_color,
            eye_color=missing_person.eye_color,
            distinctive_features=missing_person.distinctive_features,
            status=missing_person.status.value,
            last_seen_date=missing_person.last_seen_date.isoformat(),
            last_seen_location=last_seen_location,
            circumstances=missing_person.circumstances,
            found_date=missing_person.found_date.isoformat() if missing_person.found_date else None,
            found_location=found_location,
            found_condition=missing_person.found_condition,
            assigned_officer_id=missing_person.assigned_officer_id,
            reporter=reporter_dict,
            created_at=missing_person.created_at.isoformat(),
            updated_at=missing_person.updated_at.isoformat()
        )