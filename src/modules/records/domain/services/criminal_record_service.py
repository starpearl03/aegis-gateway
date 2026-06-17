# ===== criminal/services/criminal_record_service.py =====
from typing import List, Dict, Any
from datetime import datetime

from src.modules.records.domain.models.crime import Crime
from src.modules.records.domain.models.crime_victim import CrimeVictim
from src.modules.records.domain.models.criminal import Criminal
from src.modules.records.domain.models.enums import CrimeStatus, PunishmentType, PunishmentStatus
from src.modules.records.domain.models.evidence import Evidence
from src.modules.records.domain.models.punishment import Punishment
from src.modules.records.domain.repositories.crime_repository import CrimeRepository
from src.modules.records.domain.repositories.crime_victim_repository import CrimeVictimRepository
from src.modules.records.domain.repositories.criminal_repository import CriminalRepository
from src.modules.records.domain.repositories.evidence_repository import EvidenceRepository
from src.modules.records.domain.repositories.person_repository import PersonRepository
from src.modules.records.domain.repositories.punishment_repository import PunishmentRepository
from src.modules.records.internal.location_utils import LocationUtils
from src.modules.records.internal.person_image_utils import PersonImageUtils
from src.modules.records.presentation.dtos.record_management import CreateCriminalRequest, CriminalResponse, \
    UpdateCriminalRequest, ListCriminalsRequest, ListCriminalsResponse, DeleteResponse, CreateCrimeRequest, \
    CrimeResponse, UpdateCrimeRequest, ListCrimesRequest, ListCrimesResponse, AddCrimeVictimRequest, \
    CrimeVictimResponse, CreatePunishmentRequest, PunishmentResponse, UpdatePunishmentRequest, ListPunishmentsRequest, \
    ListPunishmentsResponse, CreateEvidenceRequest, EvidenceResponse, UpdateEvidenceRequest, ListEvidenceRequest, \
    ListEvidenceResponse
from src.shared.configs.exceptions.exceptions import AlreadyExistsException, NotFoundException, ValidationException


class CriminalRecordService:
    """Service for managing criminal records, crimes, punishments, and evidence."""

    def __init__(self):
        self.criminal_repo = CriminalRepository()
        self.crime_repo = CrimeRepository()
        self.victim_repo = CrimeVictimRepository()
        self.punishment_repo = PunishmentRepository()
        self.evidence_repo = EvidenceRepository()
        self.person_repo = PersonRepository()
        self.location_utils = LocationUtils()
        self.image_utils = PersonImageUtils()

    # ========================================================================
    # CRIMINAL MANAGEMENT
    # ========================================================================

    def create_criminal(self, request: CreateCriminalRequest) -> CriminalResponse:
        """
        Create a new criminal record.

        Args:
            request: CreateCriminalRequest DTO

        Returns:
            CriminalResponse DTO

        Raises:
            ValidationException: If data is invalid
            AlreadyExistsException: If criminal with same national_id exists
        """
        # Check if criminal with same national_id already exists
        if request.national_id:
            existing_person = self.person_repo.find_by_national_id(request.national_id)
            if existing_person and existing_person.type == 'criminal':
                raise AlreadyExistsException(
                    f"Criminal with national ID {request.national_id} already exists"
                )

        try:
            # Verify address location if provided
            if request.address_id:
                self.location_utils.get_location_by_id(request.address_id)

            # Create criminal entity
            criminal = Criminal(
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
                address_id=request.address_id,
                description=request.description,
                alias=request.alias,
                is_wanted=request.is_wanted,
                priority_level=request.priority_level,
                gang_affiliation=request.gang_affiliation,
                threat_level=request.threat_level,
                created_by=request.created_by
            )

            # Save criminal
            saved_criminal = self.criminal_repo.create(criminal)

            return self._build_criminal_response(saved_criminal)

        except NotFoundException:
            raise
        except Exception as e:
            raise ValidationException(f"Failed to create criminal record: {str(e)}")

    def update_criminal(self, request: UpdateCriminalRequest) -> CriminalResponse:
        """
        Update criminal details.

        Args:
            request: UpdateCriminalRequest DTO

        Returns:
            CriminalResponse DTO

        Raises:
            NotFoundException: If criminal not found
            ValidationException: If update data is invalid
        """
        criminal = self.criminal_repo.find_by_id(request.criminal_id)
        if not criminal:
            raise NotFoundException(f"Criminal with ID {request.criminal_id} not found")

        try:
            # Update fields if provided
            if request.alias is not None:
                criminal.alias = request.alias
            if request.is_wanted is not None:
                criminal.is_wanted = request.is_wanted
            if request.priority_level is not None:
                criminal.priority_level = request.priority_level
            if request.gang_affiliation is not None:
                criminal.gang_affiliation = request.gang_affiliation
            if request.threat_level is not None:
                criminal.threat_level = request.threat_level
            if request.updated_by is not None:
                criminal.updated_by = request.updated_by

            updated_criminal = self.criminal_repo.update(criminal)
            return self._build_criminal_response(updated_criminal)

        except Exception as e:
            raise ValidationException(f"Failed to update criminal: {str(e)}")

    def get_criminal_by_id(self, criminal_id: str) -> CriminalResponse:
        """
        Get criminal by ID.

        Args:
            criminal_id: Criminal ID

        Returns:
            CriminalResponse DTO

        Raises:
            NotFoundException: If criminal not found
        """
        criminal = self.criminal_repo.find_by_id(criminal_id)
        if not criminal:
            raise NotFoundException(f"Criminal with ID {criminal_id} not found")

        return self._build_criminal_response(criminal)

    def list_criminals(self, request: ListCriminalsRequest) -> ListCriminalsResponse:
        """
        List criminals with filters and pagination.

        Args:
            request: ListCriminalsRequest DTO

        Returns:
            ListCriminalsResponse DTO
        """
        # Build query based on filters
        if request.is_wanted is not None:
            if request.min_priority is not None:
                criminals = self.criminal_repo.find_high_priority_wanted(request.min_priority)
            else:
                criminals = self.criminal_repo.find_wanted()
        elif request.gang_affiliation:
            criminals = self.criminal_repo.find_by_gang(request.gang_affiliation)
        elif request.threat_level:
            criminals = self.criminal_repo.find_by_threat_level(request.threat_level)
        else:
            criminals = self.criminal_repo.find_all(include_deleted=request.include_deleted)

        # Pagination
        total = len(criminals)
        start = (request.page - 1) * request.per_page
        end = start + request.per_page
        paginated_criminals = criminals[start:end]

        criminal_dicts = [
            self._build_criminal_response(criminal).to_dict()
            for criminal in paginated_criminals
        ]

        return ListCriminalsResponse(
            message=f"Found {total} criminal(s)",
            criminals=criminal_dicts,
            total=total,
            page=request.page,
            per_page=request.per_page,
            total_pages=(total + request.per_page - 1) // request.per_page
        )


    def get_wanted_criminals(self) -> List[CriminalResponse]:
        """
        Get all wanted criminals.

        Returns:
            List of CriminalResponse DTOs
        """
        wanted = self.criminal_repo.find_wanted()
        return [self._build_criminal_response(criminal) for criminal in wanted]

    def delete_criminal(self, criminal_id: str) -> DeleteResponse:
        """
        Soft delete a criminal record.

        Args:
            criminal_id: Criminal ID

        Returns:
            DeleteResponse DTO

        Raises:
            NotFoundException: If criminal not found
        """
        criminal = self.criminal_repo.find_by_id(criminal_id)
        if not criminal:
            raise NotFoundException(f"Criminal with ID {criminal_id} not found")

        self.criminal_repo.delete(criminal)
        return DeleteResponse(
            message="Criminal record deleted successfully",
            id=criminal_id
        )


    # ========================================================================
    # CRIME MANAGEMENT
    # ========================================================================

    def create_crime(self, request: CreateCrimeRequest) -> CrimeResponse:
        """
        Create a new crime record.

        Args:
            request: CreateCrimeRequest DTO

        Returns:
            CrimeResponse DTO

        Raises:
            ValidationException: If data is invalid
            NotFoundException: If criminal or location not found
            AlreadyExistsException: If case number already exists
        """
        # Check if case number already exists
        existing_crime = self.crime_repo.find_by_case_number(request.case_number)
        if existing_crime:
            raise AlreadyExistsException(
                f"Crime with case number {request.case_number} already exists"
            )

        # Verify criminal exists
        criminal = self.criminal_repo.find_by_id(request.criminal_id)
        if not criminal:
            raise NotFoundException(f"Criminal with ID {request.criminal_id} not found")

        # Verify location exists
        self.location_utils.get_location_by_id(request.location_id)

        try:
            crime = Crime(
                case_number=request.case_number,
                crime_type=request.crime_type,
                description=request.description,
                date_committed=datetime.fromisoformat(request.date_committed),
                location_id=request.location_id,
                criminal_id=request.criminal_id,
                assigned_officer_id=request.assigned_officer_id,
                reported_by=request.reported_by,
                status=CrimeStatus.OPEN
            )

            saved_crime = self.crime_repo.create(crime)
            return self._build_crime_response(saved_crime)

        except Exception as e:
            raise ValidationException(f"Failed to create crime record: {str(e)}")

    def update_crime(self, request: UpdateCrimeRequest) -> CrimeResponse:
        """
        Update crime details.

        Args:
            request: UpdateCrimeRequest DTO

        Returns:
            CrimeResponse DTO

        Raises:
            NotFoundException: If crime not found
            ValidationException: If update data is invalid
        """
        crime = self.crime_repo.find_by_id(request.crime_id)
        if not crime:
            raise NotFoundException(f"Crime with ID {request.crime_id} not found")

        try:
            if request.status is not None:
                crime.status = self._get_enum_by_value(CrimeStatus, request.status)
            if request.assigned_officer_id is not None:
                crime.assigned_officer_id = request.assigned_officer_id
            if request.description is not None:
                crime.description = request.description
            if request.updated_by is not None:
                crime.updated_by = request.updated_by

            updated_crime = self.crime_repo.update(crime)
            return self._build_crime_response(updated_crime)

        except Exception as e:
            raise ValidationException(f"Failed to update crime: {str(e)}")

    def get_crime_by_id(self, crime_id: str) -> CrimeResponse:
        """
        Get crime by ID.

        Args:
            crime_id: Crime ID

        Returns:
            CrimeResponse DTO

        Raises:
            NotFoundException: If crime not found
        """
        crime = self.crime_repo.find_by_id(crime_id)
        if not crime:
            raise NotFoundException(f"Crime with ID {crime_id} not found")

        return self._build_crime_response(crime)

    def list_crimes(self, request: ListCrimesRequest) -> ListCrimesResponse:
        """
        List crimes with filters and pagination.

        Args:
            request: ListCrimesRequest DTO

        Returns:
            ListCrimesResponse DTO
        """
        # Build query based on filters
        if request.status:
            status = self._get_enum_by_value(CrimeStatus, request.status)
            crimes = self.crime_repo.find_by_status(status)
        elif request.crime_type:
            crimes = self.crime_repo.find_by_crime_type(request.crime_type)
        elif request.criminal_id:
            crimes = self.crime_repo.find_by_criminal(request.criminal_id)
        elif request.assigned_officer_id:
            crimes = self.crime_repo.find_by_officer(request.assigned_officer_id)
        else:
            crimes = self.crime_repo.find_all(include_deleted=request.include_deleted)

        # Pagination
        total = len(crimes)
        start = (request.page - 1) * request.per_page
        end = start + request.per_page
        paginated_crimes = crimes[start:end]

        crime_dicts = [
            self._build_crime_response(crime).to_dict()
            for crime in paginated_crimes
        ]

        return ListCrimesResponse(
            message=f"Found {total} crime(s)",
            crimes=crime_dicts,
            total=total,
            page=request.page,
            per_page=request.per_page,
            total_pages=(total + request.per_page - 1) // request.per_page
        )

    def assign_officer_to_crime(self, crime_id: str, officer_id: str) -> CrimeResponse:
        """
        Assign an officer to a crime.

        Args:
            crime_id: Crime ID
            officer_id: Officer user ID

        Returns:
            CrimeResponse DTO

        Raises:
            NotFoundException: If crime not found
        """
        crime = self.crime_repo.find_by_id(crime_id)
        if not crime:
            raise NotFoundException(f"Crime with ID {crime_id} not found")

        crime.assigned_officer_id = officer_id
        updated_crime = self.crime_repo.update(crime)

        return self._build_crime_response(updated_crime)

    def get_unassigned_cases(self) -> List[CrimeResponse]:
        """
        Get all unassigned crime cases.

        Returns:
            List of CrimeResponse DTOs
        """
        unassigned = self.crime_repo.find_unassigned_cases()
        return [self._build_crime_response(crime) for crime in unassigned]

    def delete_crime(self, crime_id: str) -> DeleteResponse:
        """
        Soft delete a crime record.

        Args:
            crime_id: Crime ID

        Returns:
            DeleteResponse DTO

        Raises:
            NotFoundException: If crime not found
        """
        crime = self.crime_repo.find_by_id(crime_id)
        if not crime:
            raise NotFoundException(f"Crime with ID {crime_id} not found")

        self.crime_repo.delete(crime)
        return DeleteResponse(
            message="Crime record deleted successfully",
            id=crime_id
        )


    # ========================================================================
    # CRIME VICTIM MANAGEMENT
    # ========================================================================

    def add_victim_to_crime(self, request: AddCrimeVictimRequest) -> CrimeVictimResponse:
        """
        Add a victim to a crime.

        Args:
            request: AddCrimeVictimRequest DTO

        Returns:
            CrimeVictimResponse DTO

        Raises:
            NotFoundException: If crime not found
            ValidationException: If validation fails
        """
        # Verify crime exists
        crime = self.crime_repo.find_by_id(request.crime_id)
        if not crime:
            raise NotFoundException(f"Crime with ID {request.crime_id} not found")

        try:
            victim = CrimeVictim(
                crime_id=request.crime_id,
                full_name=request.full_name.strip(),
                injury_description=request.injury_description,
                medical_report_path=request.medical_report_path,
                recorded_by=request.recorded_by
            )

            saved_victim = self.victim_repo.create(victim)
            return self._build_crime_victim_response(saved_victim)

        except Exception as e:
            raise ValidationException(f"Failed to add victim: {str(e)}")

    def get_crime_victims(self, crime_id: str) -> List[CrimeVictimResponse]:
        """
        Get all victims of a crime.

        Args:
            crime_id: Crime ID

        Returns:
            List of CrimeVictimResponse DTOs

        Raises:
            NotFoundException: If crime not found
        """
        crime = self.crime_repo.find_by_id(crime_id)
        if not crime:
            raise NotFoundException(f"Crime with ID {crime_id} not found")

        victims = self.victim_repo.find_by_crime(crime_id)
        return [self._build_crime_victim_response(victim) for victim in victims]

    # ========================================================================
    # PUNISHMENT MANAGEMENT
    # ========================================================================

    def create_punishment(self, request: CreatePunishmentRequest) -> PunishmentResponse:
        """
        Create a punishment for a crime.

        Args:
            request: CreatePunishmentRequest DTO

        Returns:
            PunishmentResponse DTO

        Raises:
            NotFoundException: If crime or location not found
            ValidationException: If data is invalid
        """
        # Verify crime exists
        crime = self.crime_repo.find_by_id(request.crime_id)
        if not crime:
            raise NotFoundException(f"Crime with ID {request.crime_id} not found")

        # Verify location if provided
        if request.location_id:
            self.location_utils.get_location_by_id(request.location_id)

        try:
            # Convert string values to enums using helper method
            punishment_type = self._get_enum_by_value(PunishmentType, request.type)
            punishment_status = self._get_enum_by_value(PunishmentStatus, request.status)

            punishment = Punishment(
                crime_id=request.crime_id,
                type=punishment_type,
                status=punishment_status,
                start_date=datetime.fromisoformat(request.start_date) if request.start_date else None,
                end_date=datetime.fromisoformat(request.end_date) if request.end_date else None,
                amount=request.amount,
                duration=request.duration,
                location_id=request.location_id,
                details=request.details,
                assigned_by=request.assigned_by
            )

            saved_punishment = self.punishment_repo.create(punishment)
            return self._build_punishment_response(saved_punishment)

        except Exception as e:
            raise ValidationException(f"Failed to create punishment: {str(e)}")

    def update_punishment(self, request: UpdatePunishmentRequest) -> PunishmentResponse:
        """
        Update punishment details.

        Args:
            request: UpdatePunishmentRequest DTO

        Returns:
            PunishmentResponse DTO

        Raises:
            NotFoundException: If punishment not found
            ValidationException: If update data is invalid
        """
        punishment = self.punishment_repo.find_by_id(request.punishment_id)
        if not punishment:
            raise NotFoundException(f"Punishment with ID {request.punishment_id} not found")

        try:
            if request.status is not None:
                # Convert string to enum by value using helper method
                punishment.status = self._get_enum_by_value(PunishmentStatus, request.status)
            if request.amount_paid is not None:
                punishment.amount_paid = request.amount_paid
            if request.end_date is not None:
                punishment.end_date = datetime.fromisoformat(request.end_date)
            if request.details is not None:
                punishment.details = request.details
            if request.updated_by is not None:
                punishment.updated_by = request.updated_by

            updated_punishment = self.punishment_repo.update(punishment)
            return self._build_punishment_response(updated_punishment)

        except Exception as e:
            raise ValidationException(f"Failed to update punishment: {str(e)}")

    def list_punishments(self, request: ListPunishmentsRequest) -> ListPunishmentsResponse:
        """
        List punishments with filters and pagination.

        Args:
            request: ListPunishmentsRequest DTO

        Returns:
            ListPunishmentsResponse DTO
        """
        # Build query based on filters
        if request.crime_id:
            punishments = self.punishment_repo.find_by_crime(request.crime_id)
        elif request.type:
            pun_type = self._get_enum_by_value(PunishmentType, request.type)
            punishments = self.punishment_repo.find_by_type(pun_type)
        elif request.status:
            status = self._get_enum_by_value(PunishmentStatus, request.status)
            punishments = self.punishment_repo.find_by_status(status)
        else:
            punishments = self.punishment_repo.find_all(include_deleted=request.include_deleted)

        # Pagination
        total = len(punishments)
        start = (request.page - 1) * request.per_page
        end = start + request.per_page
        paginated_punishments = punishments[start:end]

        punishment_dicts = [
            self._build_punishment_response(punishment).to_dict()
            for punishment in paginated_punishments
        ]

        return ListPunishmentsResponse(
            message=f"Found {total} punishment(s)",
            punishments=punishment_dicts,
            total=total,
            page=request.page,
            per_page=request.per_page,
            total_pages=(total + request.per_page - 1) // request.per_page
        )

    def record_fine_payment(self, punishment_id: str, amount: float) -> PunishmentResponse:
        """
        Record a payment for a fine.

        Args:
            punishment_id: Punishment ID
            amount: Amount paid

        Returns:
            PunishmentResponse DTO

        Raises:
            NotFoundException: If punishment not found
            ValidationException: If punishment is not a fine or amount is invalid
        """
        punishment = self.punishment_repo.find_by_id(punishment_id)
        if not punishment:
            raise NotFoundException(f"Punishment with ID {punishment_id} not found")

        if punishment.type != PunishmentType.FINE:
            raise ValidationException("Can only record payments for fines")

        if amount <= 0:
            raise ValidationException("Payment amount must be greater than 0")

        punishment.amount_paid = (punishment.amount_paid or 0) + amount

        # Update status if fully paid
        if punishment.amount_paid >= punishment.amount:
            punishment.status = PunishmentStatus.COMPLETED

        updated_punishment = self.punishment_repo.update(punishment)
        return self._build_punishment_response(updated_punishment)

    # ========================================================================
    # EVIDENCE MANAGEMENT
    # ========================================================================

    def create_evidence(self, request: CreateEvidenceRequest) -> EvidenceResponse:
        """
        Create evidence for a crime.

        Args:
            request: CreateEvidenceRequest DTO

        Returns:
            EvidenceResponse DTO

        Raises:
            NotFoundException: If crime not found
            ValidationException: If data is invalid
        """
        # Verify crime exists
        crime = self.crime_repo.find_by_id(request.crime_id)
        if not crime:
            raise NotFoundException(f"Crime with ID {request.crime_id} not found")

        try:
            evidence = Evidence(
                crime_id=request.crime_id,
                description=request.description,
                type=request.type,
                file_path=request.file_path,
                collected_by=request.collected_by,
                collected_date=datetime.fromisoformat(request.collected_date) if request.collected_date else None,
                storage_location=request.storage_location
            )

            saved_evidence = self.evidence_repo.create(evidence)
            return self._build_evidence_response(saved_evidence)

        except Exception as e:
            raise ValidationException(f"Failed to create evidence: {str(e)}")

    def update_evidence(self, request: UpdateEvidenceRequest) -> EvidenceResponse:
        """
        Update evidence details.

        Args:
            request: UpdateEvidenceRequest DTO

        Returns:
            EvidenceResponse DTO

        Raises:
            NotFoundException: If evidence not found
            ValidationException: If update data is invalid
        """
        evidence = self.evidence_repo.find_by_id(request.evidence_id)
        if not evidence:
            raise NotFoundException(f"Evidence with ID {request.evidence_id} not found")

        try:
            if request.description is not None:
                evidence.description = request.description
            if request.storage_location is not None:
                evidence.storage_location = request.storage_location
            if request.updated_by is not None:
                evidence.updated_by = request.updated_by

            updated_evidence = self.evidence_repo.update(evidence)
            return self._build_evidence_response(updated_evidence)

        except Exception as e:
            raise ValidationException(f"Failed to update evidence: {str(e)}")

    def list_evidence(self, request: ListEvidenceRequest) -> ListEvidenceResponse:
        """
        List evidence with filters and pagination.

        Args:
            request: ListEvidenceRequest DTO

        Returns:
            ListEvidenceResponse DTO
        """
        # Build query based on filters
        if request.crime_id:
            evidence_list = self.evidence_repo.find_by_crime(request.crime_id)
        elif request.type:
            evidence_list = self.evidence_repo.find_by_type(request.type)
        elif request.collected_by:
            evidence_list = self.evidence_repo.find_by_collector(request.collected_by)
        else:
            evidence_list = self.evidence_repo.find_all(include_deleted=request.include_deleted)

        # Pagination
        total = len(evidence_list)
        start = (request.page - 1) * request.per_page
        end = start + request.per_page
        paginated_evidence = evidence_list[start:end]

        evidence_dicts = [
            self._build_evidence_response(evidence).to_dict()
            for evidence in paginated_evidence
        ]

        return ListEvidenceResponse(
            message=f"Found {total} evidence item(s)",
            evidence=evidence_dicts,
            total=total,
            page=request.page,
            per_page=request.per_page,
            total_pages=(total + request.per_page - 1) // request.per_page
        )

    # ========================================================================
    # STATISTICS
    # ========================================================================

    def get_criminal_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for criminal records.

        Returns:
            Dictionary with statistics
        """
        total_criminals = self.criminal_repo.count()
        wanted = len(self.criminal_repo.find_wanted())
        high_priority = len(self.criminal_repo.find_high_priority_wanted(min_priority=3))

        total_crimes = self.crime_repo.count()
        open_crimes = len(self.crime_repo.find_open_cases())
        unassigned = len(self.crime_repo.find_unassigned_cases())

        total_punishments = self.punishment_repo.count()
        active_punishments = len(self.punishment_repo.find_active_punishments())
        unpaid_fines = len(self.punishment_repo.find_unpaid_fines())

        return {
            'total_criminals': total_criminals,
            'wanted_criminals': wanted,
            'high_priority_wanted': high_priority,
            'total_crimes': total_crimes,
            'open_crimes': open_crimes,
            'unassigned_crimes': unassigned,
            'total_punishments': total_punishments,
            'active_punishments': active_punishments,
            'unpaid_fines': unpaid_fines
        }

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _build_criminal_response(self, criminal: Criminal) -> CriminalResponse:
        """
        Helper method to build CriminalResponse from entity.

        Args:
            criminal: Criminal entity

        Returns:
            CriminalResponse DTO
        """
        # Get primary image
        primary_image = None
        primary_image_obj = criminal.images.filter_by(is_primary=True).first()
        if primary_image_obj:
            primary_image = primary_image_obj.image_path

        return CriminalResponse(
            id=criminal.id,
            first_name=criminal.first_name,
            last_name=criminal.last_name,
            date_of_birth=criminal.date_of_birth.isoformat() if criminal.date_of_birth else None,
            gender=criminal.gender.value if criminal.gender else None,
            national_id=criminal.national_id,
            phone_number=criminal.phone_number,
            email=criminal.email,
            alias=criminal.alias,
            is_wanted=criminal.is_wanted,
            priority_level=criminal.priority_level,
            gang_affiliation=criminal.gang_affiliation,
            threat_level=criminal.threat_level.value if criminal.threat_level else None,
            height=criminal.height,
            weight=criminal.weight,
            hair_color=criminal.hair_color,
            eye_color=criminal.eye_color,
            skin_tone=criminal.skin_tone,
            distinctive_features=criminal.distinctive_features,
            description=criminal.description,
            primary_image=primary_image,
            created_at=criminal.created_at.isoformat(),
            updated_at=criminal.updated_at.isoformat()
        )

    def _build_crime_response(self, crime: Crime) -> CrimeResponse:
        """Build CrimeResponse DTO from entity."""
        # Get location details
        location = None
        if crime.location_id:
            try:
                loc = self.location_utils.get_location_by_id(crime.location_id)
                location = loc.to_dict()
            except NotFoundException:
                pass

        return CrimeResponse(
            id=crime.id,
            case_number=crime.case_number,
            crime_type=crime.crime_type,
            description=crime.description,
            date_committed=crime.date_committed.isoformat(),
            date_reported=crime.date_reported.isoformat(),
            status=crime.status.value,
            location=location,
            criminal_id=crime.criminal_id,
            assigned_officer_id=crime.assigned_officer_id,
            created_at=crime.created_at.isoformat(),
            updated_at=crime.updated_at.isoformat()
        )

    def _build_crime_victim_response(self, victim: CrimeVictim) -> CrimeVictimResponse:
        """Build CrimeVictimResponse DTO from entity."""
        return CrimeVictimResponse(
            id=victim.id,
            crime_id=victim.crime_id,
            full_name=victim.full_name,
            injury_description=victim.injury_description,
            medical_report_path=victim.medical_report_path,
            created_at=victim.created_at.isoformat(),
            updated_at=victim.updated_at.isoformat()
        )

    def _build_punishment_response(self, punishment: Punishment) -> PunishmentResponse:
        """Build PunishmentResponse DTO from entity."""
        # Get location details
        location = None
        if punishment.location_id:
            try:
                loc = self.location_utils.get_location_by_id(punishment.location_id)
                location = loc.to_dict()
            except NotFoundException:
                pass

        return PunishmentResponse(
            id=punishment.id,
            crime_id=punishment.crime_id,
            type=punishment.type.value,
            status=punishment.status.value,
            start_date=punishment.start_date.isoformat() if punishment.start_date else None,
            end_date=punishment.end_date.isoformat() if punishment.end_date else None,
            amount=punishment.amount,
            amount_paid=punishment.amount_paid,
            duration=punishment.duration,
            location=location,
            details=punishment.details,
            created_at=punishment.created_at.isoformat(),
            updated_at=punishment.updated_at.isoformat()
        )

    def _build_evidence_response(self, evidence: Evidence) -> EvidenceResponse:
        """Build EvidenceResponse DTO from entity."""
        return EvidenceResponse(
            id=evidence.id,
            crime_id=evidence.crime_id,
            description=evidence.description,
            type=evidence.type.value,
            file_path=evidence.file_path,
            collected_by=evidence.collected_by,
            collected_date=evidence.collected_date.isoformat() if evidence.collected_date else None,
            storage_location=evidence.storage_location,
            created_at=evidence.created_at.isoformat(),
            updated_at=evidence.updated_at.isoformat()
        )

    # ========================================================================
    # HELPER METHOD FOR ENUM CONVERSION
    # ========================================================================

    @staticmethod
    def _get_enum_by_value(enum_class, value: str):
        """
        Get enum member by its value (case-insensitive).

        Args:
            enum_class: The enum class to search
            value: The string value to find

        Returns:
            The matching enum member

        Raises:
            ValidationException: If no matching enum member is found
        """
        if not value:
            raise ValidationException(f"Value cannot be empty for {enum_class.__name__}")

        value_lower = value.lower().strip()
        for member in enum_class:
            if member.value.lower() == value_lower:
                return member

        # Build helpful error message with valid options
        valid_values = [member.value for member in enum_class]
        raise ValidationException(
            f"Invalid {enum_class.__name__} value: '{value}'. "
            f"Valid options are: {', '.join(valid_values)}"
        )
