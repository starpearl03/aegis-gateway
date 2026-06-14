from dataclasses import dataclass
from typing import Dict, Any, Optional, List
import re
from src.shared.configs.exceptions.exceptions import ValidationException


# ============================================================================
# SHARED DTOs - Location
# ============================================================================

@dataclass
class CreateLocationRequest:
    """DTO for creating a location."""
    latitude: float
    longitude: float
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None

    def __post_init__(self):
        """Validate location data."""
        self._validate_coordinates(self.latitude, self.longitude)

    @staticmethod
    def _validate_coordinates(latitude: float, longitude: float) -> None:
        """Validate GPS coordinates."""
        if not -90 <= latitude <= 90:
            raise ValidationException("Latitude must be between -90 and 90")
        if not -180 <= longitude <= 180:
            raise ValidationException("Longitude must be between -180 and 180")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'postal_code': self.postal_code,
            'description': self.description,
            'created_by': self.created_by
        }


@dataclass
class LocationResponse:
    """DTO for location response."""
    id: str
    latitude: float
    longitude: float
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    postal_code: Optional[str]
    description: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'latitude': float(self.latitude),
            'longitude': float(self.longitude),
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'country': self.country,
            'postal_code': self.postal_code,
            'description': self.description,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


# ============================================================================
# SHARED DTOs - Person
# ============================================================================

@dataclass
class CreatePersonRequest:
    """DTO for creating a person."""
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None  # ISO format: YYYY-MM-DD
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    national_id: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    skin_tone: Optional[str] = None
    distinctive_features: Optional[str] = None
    address_id: Optional[str] = None
    description: Optional[str] = None
    created_by: Optional[str] = None

    def __post_init__(self):
        """Validate person data."""
        self._validate_name(self.first_name, "First name")
        self._validate_name(self.last_name, "Last name")
        if self.email:
            self._validate_email(self.email)
        if self.phone_number:
            self._validate_phone(self.phone_number)

    @staticmethod
    def _validate_name(name: str, field_name: str = "Name") -> None:
        """Validate name field."""
        if not name or not name.strip():
            raise ValidationException(f"{field_name} cannot be empty")
        if len(name.strip()) < 2:
            raise ValidationException(f"{field_name} must be at least 2 characters long")
        if len(name) > 100:
            raise ValidationException(f"{field_name} is too long")

    @staticmethod
    def _validate_email(email: str) -> None:
        """Validate email format."""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValidationException("Invalid email format")
        if len(email) > 100:
            raise ValidationException("Email is too long")

    @staticmethod
    def _validate_phone(phone: str) -> None:
        """Validate phone number."""
        if len(phone) > 20:
            raise ValidationException("Phone number is too long")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'phone_number': self.phone_number,
            'email': self.email,
            'national_id': self.national_id,
            'height': self.height,
            'weight': self.weight,
            'hair_color': self.hair_color,
            'eye_color': self.eye_color,
            'skin_tone': self.skin_tone,
            'distinctive_features': self.distinctive_features,
            'address_id': self.address_id,
            'description': self.description,
            'created_by': self.created_by
        }


@dataclass
class PersonResponse:
    """DTO for person response."""
    id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[str]
    gender: Optional[str]
    phone_number: Optional[str]
    email: Optional[str]
    national_id: Optional[str]
    height: Optional[float]
    weight: Optional[float]
    hair_color: Optional[str]
    eye_color: Optional[str]
    skin_tone: Optional[str]
    distinctive_features: Optional[str]
    description: Optional[str]
    type: str
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'phone_number': self.phone_number,
            'email': self.email,
            'national_id': self.national_id,
            'height': self.height,
            'weight': self.weight,
            'hair_color': self.hair_color,
            'eye_color': self.eye_color,
            'skin_tone': self.skin_tone,
            'distinctive_features': self.distinctive_features,
            'description': self.description,
            'type': self.type,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


# ============================================================================
# SHARED DTOs - Person Image
# ============================================================================

@dataclass
class CreatePersonImageRequest:
    """DTO for uploading a person image."""
    person_id: str
    image_path: str
    is_primary: bool = False
    quality_score: Optional[float] = None
    uploaded_by: Optional[str] = None

    def __post_init__(self):
        """Validate image data."""
        if not self.person_id:
            raise ValidationException("Person ID is required")
        if not self.image_path:
            raise ValidationException("Image path is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'person_id': self.person_id,
            'image_path': self.image_path,
            'is_primary': self.is_primary,
            'quality_score': self.quality_score,
            'uploaded_by': self.uploaded_by
        }


@dataclass
class PersonImageResponse:
    """DTO for person image response."""
    id: str
    person_id: str
    image_path: str
    is_primary: bool
    quality_score: Optional[float]
    capture_date: str
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'person_id': self.person_id,
            'image_path': self.image_path,
            'is_primary': self.is_primary,
            'quality_score': self.quality_score,
            'capture_date': self.capture_date,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


# ============================================================================
# MISSING PERSON DTOs
# ============================================================================

@dataclass
class CreateMissingPersonRequest:
    """DTO for reporting a missing person."""
    # Required fields first
    first_name: str
    last_name: str
    last_seen_date: str  # ISO format datetime
    last_seen_location_id: str
    reporter_first_name: str
    reporter_last_name: str
    reporter_relationship: str
    reporter_phone: str

    # Optional fields after
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    national_id: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    skin_tone: Optional[str] = None
    distinctive_features: Optional[str] = None
    description: Optional[str] = None
    circumstances: Optional[str] = None
    assigned_officer_id: Optional[str] = None
    reporter_email: Optional[str] = None
    reporter_address_id: Optional[str] = None
    created_by: Optional[str] = None

    def __post_init__(self):
        """Validate missing person data."""
        self._validate_name(self.first_name, "First name")
        self._validate_name(self.last_name, "Last name")
        self._validate_name(self.reporter_first_name, "Reporter first name")
        self._validate_name(self.reporter_last_name, "Reporter last name")

        if not self.last_seen_date:
            raise ValidationException("Last seen date is required")
        if not self.last_seen_location_id:
            raise ValidationException("Last seen location is required")
        if not self.reporter_relationship:
            raise ValidationException("Reporter relationship is required")
        if not self.reporter_phone:
            raise ValidationException("Reporter phone is required")

    @staticmethod
    def _validate_name(name: str, field_name: str) -> None:
        """Validate name field."""
        if not name or not name.strip():
            raise ValidationException(f"{field_name} cannot be empty")
        if len(name.strip()) < 2:
            raise ValidationException(f"{field_name} must be at least 2 characters long")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'phone_number': self.phone_number,
            'email': self.email,
            'national_id': self.national_id,
            'height': self.height,
            'weight': self.weight,
            'hair_color': self.hair_color,
            'eye_color': self.eye_color,
            'skin_tone': self.skin_tone,
            'distinctive_features': self.distinctive_features,
            'description': self.description,
            'last_seen_date': self.last_seen_date,
            'last_seen_location_id': self.last_seen_location_id,
            'circumstances': self.circumstances,
            'assigned_officer_id': self.assigned_officer_id,
            'reporter_first_name': self.reporter_first_name,
            'reporter_last_name': self.reporter_last_name,
            'reporter_relationship': self.reporter_relationship,
            'reporter_phone': self.reporter_phone,
            'reporter_email': self.reporter_email,
            'reporter_address_id': self.reporter_address_id,
            'created_by': self.created_by
        }


@dataclass
class UpdateMissingPersonRequest:
    """DTO for updating missing person details."""
    missing_person_id: str
    status: Optional[str] = None
    circumstances: Optional[str] = None
    found_date: Optional[str] = None
    found_location_id: Optional[str] = None
    found_condition: Optional[str] = None
    assigned_officer_id: Optional[str] = None
    updated_by: Optional[str] = None

    def __post_init__(self):
        """Validate update data."""
        if not self.missing_person_id:
            raise ValidationException("Missing person ID is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {'missing_person_id': self.missing_person_id}
        if self.status is not None:
            data['status'] = self.status
        if self.circumstances is not None:
            data['circumstances'] = self.circumstances
        if self.found_date is not None:
            data['found_date'] = self.found_date
        if self.found_location_id is not None:
            data['found_location_id'] = self.found_location_id
        if self.found_condition is not None:
            data['found_condition'] = self.found_condition
        if self.assigned_officer_id is not None:
            data['assigned_officer_id'] = self.assigned_officer_id
        if self.updated_by is not None:
            data['updated_by'] = self.updated_by
        return data


@dataclass
class MissingPersonResponse:
    """DTO for missing person response."""
    id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[str]
    gender: Optional[str]
    phone_number: Optional[str]
    email: Optional[str]
    national_id: Optional[str]
    height: Optional[float]
    weight: Optional[float]
    hair_color: Optional[str]
    eye_color: Optional[str]
    skin_tone: Optional[str]
    distinctive_features: Optional[str]
    status: str
    last_seen_date: str
    last_seen_location: Optional[Dict[str, Any]]
    circumstances: Optional[str]
    found_date: Optional[str]
    found_location: Optional[Dict[str, Any]]
    found_condition: Optional[str]
    assigned_officer_id: Optional[str]
    reporter: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'phone_number': self.phone_number,
            'email': self.email,
            'national_id': self.national_id,
            'height': self.height,
            'weight': self.weight,
            'hair_color': self.hair_color,
            'eye_color': self.eye_color,
            'skin_tone': self.skin_tone,
            'distinctive_features': self.distinctive_features,
            'status': self.status,
            'last_seen_date': self.last_seen_date,
            'last_seen_location': self.last_seen_location,
            'circumstances': self.circumstances,
            'found_date': self.found_date,
            'found_location': self.found_location,
            'found_condition': self.found_condition,
            'assigned_officer_id': self.assigned_officer_id,
            'reporter': self.reporter,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class UpdateMissingPersonStatusRequest:
    """DTO for updating missing person status."""
    missing_person_id: str
    new_status: str
    changed_by: str
    notes: Optional[str] = None

    def __post_init__(self):
        """Validate status update data."""
        if not self.missing_person_id:
            raise ValidationException("Missing person ID is required")
        if not self.new_status:
            raise ValidationException("New status is required")
        if not self.changed_by:
            raise ValidationException("Changed by user ID is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'missing_person_id': self.missing_person_id,
            'new_status': self.new_status,
            'notes': self.notes,
            'changed_by': self.changed_by
        }


@dataclass
class ListMissingPersonsRequest:
    """DTO for listing missing persons with filters."""
    page: int = 1
    per_page: int = 20
    status: Optional[str] = None
    assigned_officer_id: Optional[str] = None
    include_deleted: bool = False

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValidationException("Page must be at least 1")
        if self.per_page < 1 or self.per_page > 100:
            raise ValidationException("Per page must be between 1 and 100")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'page': self.page,
            'per_page': self.per_page,
            'include_deleted': self.include_deleted
        }
        if self.status is not None:
            data['status'] = self.status
        if self.assigned_officer_id is not None:
            data['assigned_officer_id'] = self.assigned_officer_id
        return data


@dataclass
class ListMissingPersonsResponse:
    """DTO for list missing persons response."""
    message: str
    missing_persons: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'missing_persons': self.missing_persons,
            'pagination': {
                'total': self.total,
                'page': self.page,
                'per_page': self.per_page,
                'total_pages': self.total_pages
            }
        }


# ============================================================================
# CRIMINAL DTOs
# ============================================================================

@dataclass
class CreateCriminalRequest:
    """DTO for creating a criminal record."""
    # Person details
    first_name: str
    last_name: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    national_id: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    hair_color: Optional[str] = None
    eye_color: Optional[str] = None
    skin_tone: Optional[str] = None
    distinctive_features: Optional[str] = None
    address_id: Optional[str] = None
    description: Optional[str] = None

    # Criminal specific
    alias: Optional[str] = None
    is_wanted: bool = False
    priority_level: int = 0
    gang_affiliation: Optional[str] = None
    threat_level: Optional[str] = None

    created_by: Optional[str] = None

    def __post_init__(self):
        """Validate criminal data."""
        self._validate_name(self.first_name, "First name")
        self._validate_name(self.last_name, "Last name")
        if self.priority_level < 0 or self.priority_level > 5:
            raise ValidationException("Priority level must be between 0 and 5")

    @staticmethod
    def _validate_name(name: str, field_name: str) -> None:
        """Validate name field."""
        if not name or not name.strip():
            raise ValidationException(f"{field_name} cannot be empty")
        if len(name.strip()) < 2:
            raise ValidationException(f"{field_name} must be at least 2 characters long")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'phone_number': self.phone_number,
            'email': self.email,
            'national_id': self.national_id,
            'height': self.height,
            'weight': self.weight,
            'hair_color': self.hair_color,
            'eye_color': self.eye_color,
            'skin_tone': self.skin_tone,
            'distinctive_features': self.distinctive_features,
            'address_id': self.address_id,
            'description': self.description,
            'alias': self.alias,
            'is_wanted': self.is_wanted,
            'priority_level': self.priority_level,
            'gang_affiliation': self.gang_affiliation,
            'threat_level': self.threat_level,
            'created_by': self.created_by
        }


@dataclass
class UpdateCriminalRequest:
    """DTO for updating criminal details."""
    criminal_id: str
    alias: Optional[str] = None
    is_wanted: Optional[bool] = None
    priority_level: Optional[int] = None
    gang_affiliation: Optional[str] = None
    threat_level: Optional[str] = None
    updated_by: Optional[str] = None

    def __post_init__(self):
        """Validate update data."""
        if not self.criminal_id:
            raise ValidationException("Criminal ID is required")
        if self.priority_level is not None and (self.priority_level < 0 or self.priority_level > 5):
            raise ValidationException("Priority level must be between 0 and 5")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {'criminal_id': self.criminal_id}
        if self.alias is not None:
            data['alias'] = self.alias
        if self.is_wanted is not None:
            data['is_wanted'] = self.is_wanted
        if self.priority_level is not None:
            data['priority_level'] = self.priority_level
        if self.gang_affiliation is not None:
            data['gang_affiliation'] = self.gang_affiliation
        if self.threat_level is not None:
            data['threat_level'] = self.threat_level
        if self.updated_by is not None:
            data['updated_by'] = self.updated_by
        return data


@dataclass
class CriminalResponse:
    """DTO for criminal response."""
    id: str
    first_name: str
    last_name: str
    date_of_birth: Optional[str]
    gender: Optional[str]
    national_id: Optional[str]
    phone_number: Optional[str]
    email: Optional[str]
    alias: Optional[str]
    is_wanted: bool
    priority_level: int
    gang_affiliation: Optional[str]
    threat_level: Optional[str]
    height: Optional[float]
    weight: Optional[float]
    hair_color: Optional[str]
    eye_color: Optional[str]
    skin_tone: Optional[str]
    distinctive_features: Optional[str]
    description: Optional[str]
    primary_image: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth,
            'gender': self.gender,
            'national_id': self.national_id,
            'phone_number': self.phone_number,
            'email': self.email,
            'alias': self.alias,
            'is_wanted': self.is_wanted,
            'priority_level': self.priority_level,
            'gang_affiliation': self.gang_affiliation,
            'threat_level': self.threat_level,
            'height': self.height,
            'weight': self.weight,
            'hair_color': self.hair_color,
            'eye_color': self.eye_color,
            'skin_tone': self.skin_tone,
            'distinctive_features': self.distinctive_features,
            'description': self.description,
            'primary_image': self.primary_image,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class ListCriminalsRequest:
    """DTO for listing criminals with filters."""
    page: int = 1
    per_page: int = 20
    is_wanted: Optional[bool] = None
    min_priority: Optional[int] = None
    gang_affiliation: Optional[str] = None
    threat_level: Optional[str] = None
    include_deleted: bool = False

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValidationException("Page must be at least 1")
        if self.per_page < 1 or self.per_page > 100:
            raise ValidationException("Per page must be between 1 and 100")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'page': self.page,
            'per_page': self.per_page,
            'include_deleted': self.include_deleted
        }
        if self.is_wanted is not None:
            data['is_wanted'] = self.is_wanted
        if self.min_priority is not None:
            data['min_priority'] = self.min_priority
        if self.gang_affiliation is not None:
            data['gang_affiliation'] = self.gang_affiliation
        if self.threat_level is not None:
            data['threat_level'] = self.threat_level
        return data


@dataclass
class ListCriminalsResponse:
    """DTO for list criminals response."""
    message: str
    criminals: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'criminals': self.criminals,
            'pagination': {
                'total': self.total,
                'page': self.page,
                'per_page': self.per_page,
                'total_pages': self.total_pages
            }
        }


# ============================================================================
# CRIME DTOs
# ============================================================================

@dataclass
class CreateCrimeRequest:
    """DTO for creating a crime record."""
    case_number: str
    crime_type: str
    description: str
    date_committed: str  # ISO format datetime
    criminal_id: str
    location_id: str
    assigned_officer_id: Optional[str] = None
    reported_by: Optional[str] = None

    def __post_init__(self):
        """Validate crime data."""
        if not self.case_number or not self.case_number.strip():
            raise ValidationException("Case number is required")
        if not self.crime_type or not self.crime_type.strip():
            raise ValidationException("Crime type is required")
        if not self.description or not self.description.strip():
            raise ValidationException("Description is required")
        if not self.date_committed:
            raise ValidationException("Date committed is required")
        if not self.criminal_id:
            raise ValidationException("Criminal ID is required")
        if not self.location_id:
            raise ValidationException("Location ID is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'case_number': self.case_number,
            'crime_type': self.crime_type,
            'description': self.description,
            'date_committed': self.date_committed,
            'criminal_id': self.criminal_id,
            'location_id': self.location_id,
            'assigned_officer_id': self.assigned_officer_id,
            'reported_by': self.reported_by
        }


@dataclass
class UpdateCrimeRequest:
    """DTO for updating crime details."""
    crime_id: str
    status: Optional[str] = None
    assigned_officer_id: Optional[str] = None
    description: Optional[str] = None
    updated_by: Optional[str] = None

    def __post_init__(self):
        """Validate update data."""
        if not self.crime_id:
            raise ValidationException("Crime ID is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {'crime_id': self.crime_id}
        if self.status is not None:
            data['status'] = self.status
        if self.assigned_officer_id is not None:
            data['assigned_officer_id'] = self.assigned_officer_id
        if self.description is not None:
            data['description'] = self.description
        if self.updated_by is not None:
            data['updated_by'] = self.updated_by
        return data


@dataclass
class CrimeResponse:
    """DTO for crime response."""
    id: str
    case_number: str
    crime_type: str
    description: str
    date_committed: str
    date_reported: str
    status: str
    location: Optional[Dict[str, Any]]
    criminal_id: str
    assigned_officer_id: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'case_number': self.case_number,
            'crime_type': self.crime_type,
            'description': self.description,
            'date_committed': self.date_committed,
            'date_reported': self.date_reported,
            'status': self.status,
            'location': self.location,
            'criminal_id': self.criminal_id,
            'assigned_officer_id': self.assigned_officer_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class AddCrimeVictimRequest:
    """DTO for adding a victim to a crime."""
    crime_id: str
    full_name: str  # Changed from person_id
    injury_description: Optional[str] = None
    medical_report_path: Optional[str] = None
    recorded_by: Optional[str] = None

    def __post_init__(self):
        """Validate victim data."""
        if not self.crime_id:
            raise ValidationException("Crime ID is required")
        if not self.full_name or not self.full_name.strip():
            raise ValidationException("Victim full name is required")
        if len(self.full_name.strip()) < 2:
            raise ValidationException("Victim full name must be at least 2 characters long")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'crime_id': self.crime_id,
            'full_name': self.full_name,
            'injury_description': self.injury_description,
            'medical_report_path': self.medical_report_path,
            'recorded_by': self.recorded_by
        }


@dataclass
class CrimeVictimResponse:
    """DTO for crime victim response."""
    id: str
    crime_id: str
    full_name: str  # Changed from person_id
    injury_description: Optional[str]
    medical_report_path: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'crime_id': self.crime_id,
            'full_name': self.full_name,
            'injury_description': self.injury_description,
            'medical_report_path': self.medical_report_path,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class ListCrimesRequest:
    """DTO for listing crimes with filters."""
    page: int = 1
    per_page: int = 20
    status: Optional[str] = None
    crime_type: Optional[str] = None
    criminal_id: Optional[str] = None
    assigned_officer_id: Optional[str] = None
    include_deleted: bool = False

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValidationException("Page must be at least 1")
        if self.per_page < 1 or self.per_page > 100:
            raise ValidationException("Per page must be between 1 and 100")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'page': self.page,
            'per_page': self.per_page,
            'include_deleted': self.include_deleted
        }
        if self.status is not None:
            data['status'] = self.status
        if self.crime_type is not None:
            data['crime_type'] = self.crime_type
        if self.criminal_id is not None:
            data['criminal_id'] = self.criminal_id
        if self.assigned_officer_id is not None:
            data['assigned_officer_id'] = self.assigned_officer_id
        return data


@dataclass
class ListCrimesResponse:
    """DTO for list crimes response."""
    message: str
    crimes: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'crimes': self.crimes,
            'pagination': {
                'total': self.total,
                'page': self.page,
                'per_page': self.per_page,
                'total_pages': self.total_pages
            }
        }


# ============================================================================
# PUNISHMENT DTOs
# ============================================================================

@dataclass
class CreatePunishmentRequest:
    """DTO for creating a punishment record."""
    crime_id: str
    type: str  # PunishmentType enum value
    status: str  # PunishmentStatus enum value
    start_date: Optional[str] = None  # ISO format datetime
    end_date: Optional[str] = None  # ISO format datetime
    amount: Optional[float] = None  # For fines
    duration: Optional[int] = None  # In days
    location_id: Optional[str] = None  # For jail or community service
    details: Optional[str] = None
    assigned_by: Optional[str] = None

    def __post_init__(self):
        """Validate punishment data."""
        if not self.crime_id:
            raise ValidationException("Crime ID is required")
        if not self.type:
            raise ValidationException("Punishment type is required")
        if not self.status:
            raise ValidationException("Punishment status is required")

        # Validate that type and status are valid enum values (lowercase check)
        valid_types = ['jail', 'prison', 'fine', 'probation', 'community_service',
                      'suspended_sentence', 'acquitted', 'death_penalty']
        if self.type not in valid_types:
            raise ValidationException(f"Invalid punishment type: {self.type}. Must be one of: {', '.join(valid_types)}")

        valid_statuses = ['pending', 'active', 'completed', 'suspended',
                         'revoked', 'overdue', 'partially_paid']
        if self.status not in valid_statuses:
            raise ValidationException(f"Invalid status: {self.status}. Must be one of: {', '.join(valid_statuses)}")

        # Validate fine amount if type is fine
        if self.type == 'fine':
            if self.amount is None or self.amount <= 0:
                raise ValidationException("Fine requires a valid amount greater than 0")

        # Validate duration for time-based punishments
        if self.type in ['jail', 'prison', 'community_service', 'probation']:
            if self.duration is None or self.duration <= 0:
                raise ValidationException(f"{self.type.replace('_', ' ').title()} requires a valid duration greater than 0")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'crime_id': self.crime_id,
            'type': self.type,
            'status': self.status,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'amount': self.amount,
            'duration': self.duration,
            'location_id': self.location_id,
            'details': self.details,
            'assigned_by': self.assigned_by
        }


@dataclass
class UpdatePunishmentRequest:
    """DTO for updating punishment details."""
    punishment_id: str
    status: Optional[str] = None
    amount_paid: Optional[float] = None
    end_date: Optional[str] = None
    details: Optional[str] = None
    updated_by: Optional[str] = None

    def __post_init__(self):
        """Validate update data."""
        if not self.punishment_id:
            raise ValidationException("Punishment ID is required")
        if self.amount_paid is not None and self.amount_paid < 0:
            raise ValidationException("Amount paid cannot be negative")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {'punishment_id': self.punishment_id}
        if self.status is not None:
            data['status'] = self.status
        if self.amount_paid is not None:
            data['amount_paid'] = self.amount_paid
        if self.end_date is not None:
            data['end_date'] = self.end_date
        if self.details is not None:
            data['details'] = self.details
        if self.updated_by is not None:
            data['updated_by'] = self.updated_by
        return data


@dataclass
class PunishmentResponse:
    """DTO for punishment response."""
    id: str
    crime_id: str
    type: str
    status: str
    start_date: Optional[str]
    end_date: Optional[str]
    amount: Optional[float]
    amount_paid: Optional[float]
    duration: Optional[int]
    location: Optional[Dict[str, Any]]
    details: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'crime_id': self.crime_id,
            'type': self.type,
            'status': self.status,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'amount': float(self.amount) if self.amount else None,
            'amount_paid': float(self.amount_paid) if self.amount_paid else None,
            'duration': self.duration,
            'location': self.location,
            'details': self.details,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class ListPunishmentsRequest:
    """DTO for listing punishments with filters."""
    page: int = 1
    per_page: int = 20
    crime_id: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    include_deleted: bool = False

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValidationException("Page must be at least 1")
        if self.per_page < 1 or self.per_page > 100:
            raise ValidationException("Per page must be between 1 and 100")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'page': self.page,
            'per_page': self.per_page,
            'include_deleted': self.include_deleted
        }
        if self.crime_id is not None:
            data['crime_id'] = self.crime_id
        if self.type is not None:
            data['type'] = self.type
        if self.status is not None:
            data['status'] = self.status
        return data


@dataclass
class ListPunishmentsResponse:
    """DTO for list punishments response."""
    message: str
    punishments: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'punishments': self.punishments,
            'pagination': {
                'total': self.total,
                'page': self.page,
                'per_page': self.per_page,
                'total_pages': self.total_pages
            }
        }


# ============================================================================
# EVIDENCE DTOs
# ============================================================================

@dataclass
class CreateEvidenceRequest:
    """DTO for creating an evidence record."""
    crime_id: str
    description: str
    type: str  # EvidenceType enum value
    file_path: Optional[str] = None
    collected_by: Optional[str] = None
    collected_date: Optional[str] = None  # ISO format datetime
    storage_location: Optional[str] = None

    def __post_init__(self):
        """Validate evidence data."""
        if not self.crime_id:
            raise ValidationException("Crime ID is required")
        if not self.description or not self.description.strip():
            raise ValidationException("Description is required")
        if not self.type:
            raise ValidationException("Evidence type is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'crime_id': self.crime_id,
            'description': self.description,
            'type': self.type,
            'file_path': self.file_path,
            'collected_by': self.collected_by,
            'collected_date': self.collected_date,
            'storage_location': self.storage_location
        }


@dataclass
class UpdateEvidenceRequest:
    """DTO for updating evidence details."""
    evidence_id: str
    description: Optional[str] = None
    storage_location: Optional[str] = None
    updated_by: Optional[str] = None

    def __post_init__(self):
        """Validate update data."""
        if not self.evidence_id:
            raise ValidationException("Evidence ID is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {'evidence_id': self.evidence_id}
        if self.description is not None:
            data['description'] = self.description
        if self.storage_location is not None:
            data['storage_location'] = self.storage_location
        if self.updated_by is not None:
            data['updated_by'] = self.updated_by
        return data


@dataclass
class EvidenceResponse:
    """DTO for evidence response."""
    id: str
    crime_id: str
    description: str
    type: str
    file_path: Optional[str]
    collected_by: Optional[str]
    collected_date: Optional[str]
    storage_location: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'crime_id': self.crime_id,
            'description': self.description,
            'type': self.type,
            'file_path': self.file_path,
            'collected_by': self.collected_by,
            'collected_date': self.collected_date,
            'storage_location': self.storage_location,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class ListEvidenceRequest:
    """DTO for listing evidence with filters."""
    page: int = 1
    per_page: int = 20
    crime_id: Optional[str] = None
    type: Optional[str] = None
    collected_by: Optional[str] = None
    include_deleted: bool = False

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.page < 1:
            raise ValidationException("Page must be at least 1")
        if self.per_page < 1 or self.per_page > 100:
            raise ValidationException("Per page must be between 1 and 100")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'page': self.page,
            'per_page': self.per_page,
            'include_deleted': self.include_deleted
        }
        if self.crime_id is not None:
            data['crime_id'] = self.crime_id
        if self.type is not None:
            data['type'] = self.type
        if self.collected_by is not None:
            data['collected_by'] = self.collected_by
        return data


@dataclass
class ListEvidenceResponse:
    """DTO for list evidence response."""
    message: str
    evidence: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'evidence': self.evidence,
            'pagination': {
                'total': self.total,
                'page': self.page,
                'per_page': self.per_page,
                'total_pages': self.total_pages
            }
        }


# ============================================================================
# SEARCH/FILTER DTOs
# ============================================================================

@dataclass
class SearchPersonRequest:
    """DTO for searching persons by name or other criteria."""
    query: str
    search_type: str = "name"  # name, phone, email, national_id
    page: int = 1
    per_page: int = 20

    def __post_init__(self):
        """Validate search parameters."""
        if not self.query or not self.query.strip():
            raise ValidationException("Search query cannot be empty")
        if self.search_type not in ["name", "phone", "email", "national_id"]:
            raise ValidationException("Invalid search type")
        if self.page < 1:
            raise ValidationException("Page must be at least 1")
        if self.per_page < 1 or self.per_page > 100:
            raise ValidationException("Per page must be between 1 and 100")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'query': self.query,
            'search_type': self.search_type,
            'page': self.page,
            'per_page': self.per_page
        }


@dataclass
class SearchPersonResponse:
    """DTO for search person response."""
    message: str
    results: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'results': self.results,
            'pagination': {
                'total': self.total,
                'page': self.page,
                'per_page': self.per_page,
                'total_pages': self.total_pages
            }
        }


@dataclass
class GetNearbyLocationsRequest:
    """DTO for finding locations near GPS coordinates."""
    latitude: float
    longitude: float
    radius_km: float = 1.0

    def __post_init__(self):
        """Validate location search parameters."""
        if not -90 <= self.latitude <= 90:
            raise ValidationException("Latitude must be between -90 and 90")
        if not -180 <= self.longitude <= 180:
            raise ValidationException("Longitude must be between -180 and 180")
        if self.radius_km <= 0 or self.radius_km > 100:
            raise ValidationException("Radius must be between 0 and 100 km")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'radius_km': self.radius_km
        }


@dataclass
class GetNearbyLocationsResponse:
    """DTO for nearby locations response."""
    message: str
    locations: List[Dict[str, Any]]
    total: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'locations': self.locations,
            'total': self.total
        }


# ============================================================================
# STATISTICS/DASHBOARD DTOs
# ============================================================================

@dataclass
class GetStatisticsRequest:
    """DTO for requesting statistics."""
    start_date: Optional[str] = None  # ISO format date
    end_date: Optional[str] = None  # ISO format date
    officer_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {}
        if self.start_date is not None:
            data['start_date'] = self.start_date
        if self.end_date is not None:
            data['end_date'] = self.end_date
        if self.officer_id is not None:
            data['officer_id'] = self.officer_id
        return data


@dataclass
class StatisticsResponse:
    """DTO for statistics response."""
    message: str
    total_missing_persons: int
    active_missing_cases: int
    total_criminals: int
    wanted_criminals: int
    total_crimes: int
    open_crimes: int
    solved_crimes: int
    total_punishments: int
    active_punishments: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'statistics': {
                'missing_persons': {
                    'total': self.total_missing_persons,
                    'active_cases': self.active_missing_cases
                },
                'criminals': {
                    'total': self.total_criminals,
                    'wanted': self.wanted_criminals
                },
                'crimes': {
                    'total': self.total_crimes,
                    'open': self.open_crimes,
                    'solved': self.solved_crimes
                },
                'punishments': {
                    'total': self.total_punishments,
                    'active': self.active_punishments
                }
            }
        }


# ============================================================================
# COMMON RESPONSE DTOs
# ============================================================================

@dataclass
class DeleteResponse:
    """Generic delete response DTO."""
    message: str
    id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'id': self.id
        }