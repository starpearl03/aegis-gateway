# ===== src/modules/identification/application/dtos/identification_dtos.py =====
from dataclasses import dataclass
from typing import Dict, Any, Optional, List
from src.shared.configs.exceptions.exceptions import ValidationException


# ============================================================================
# IDENTIFICATION SEARCH DTOs
# ============================================================================

@dataclass
class CreateIdentificationSearchRequest:
    """DTO for creating an identification search."""
    search_type: str  # 'criminal' or 'missing_person'
    file_path: str
    file_type: str  # 'image' or 'video'

    def __post_init__(self):
        """Validate identification search data."""
        if not self.search_type:
            raise ValidationException("Search type is required")

        valid_search_types = ['criminal', 'missing_person']
        if self.search_type not in valid_search_types:
            raise ValidationException(
                f"Invalid search type: {self.search_type}. Must be one of: {', '.join(valid_search_types)}"
            )

        if not self.file_path or not self.file_path.strip():
            raise ValidationException("File path is required")

        if not self.file_type:
            raise ValidationException("File type is required")

        valid_file_types = ['image', 'video']
        if self.file_type not in valid_file_types:
            raise ValidationException(
                f"Invalid file type: {self.file_type}. Must be one of: {', '.join(valid_file_types)}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'search_type': self.search_type,
            'file_path': self.file_path,
            'file_type': self.file_type
        }


@dataclass
class IdentificationSearchResponse:
    """DTO for identification search response."""
    id: str
    search_type: str
    file_path: str
    file_type: str
    status: str
    notification_sent: bool
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'search_type': self.search_type,
            'file_path': self.file_path,
            'file_type': self.file_type,
            'status': self.status,
            'notification_sent': self.notification_sent,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class ListIdentificationSearchesRequest:
    """DTO for listing identification searches with filters."""
    page: int = 1
    per_page: int = 20
    search_type: Optional[str] = None
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
        if self.search_type is not None:
            data['search_type'] = self.search_type
        if self.status is not None:
            data['status'] = self.status
        return data


@dataclass
class ListIdentificationSearchesResponse:
    """DTO for list identification searches response."""
    message: str
    searches: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    total_pages: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'searches': self.searches,
            'pagination': {
                'total': self.total,
                'page': self.page,
                'per_page': self.per_page,
                'total_pages': self.total_pages
            }
        }


# ============================================================================
# IDENTIFICATION RESULT DTOs
# ============================================================================

@dataclass
class IdentificationResultResponse:
    """DTO for identification result response."""
    id: str
    search_id: str
    person_id: Optional[str]
    person_type: Optional[str]
    similarity_score: float
    is_match: bool
    matched_image_id: Optional[str]
    person_details: Optional[Dict[str, Any]]
    matched_image_path: Optional[str]
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'search_id': self.search_id,
            'person_id': self.person_id,
            'person_type': self.person_type,
            'similarity_score': self.similarity_score,
            'is_match': self.is_match,
            'matched_image_id': self.matched_image_id,
            'person_details': self.person_details,
            'matched_image_path': self.matched_image_path,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }


@dataclass
class GetSearchResultsRequest:
    """DTO for getting search results with filters."""
    search_id: str
    matches_only: bool = True
    limit: Optional[int] = None

    def __post_init__(self):
        """Validate request parameters."""
        if not self.search_id:
            raise ValidationException("Search ID is required")
        if self.limit is not None and (self.limit < 1 or self.limit > 100):
            raise ValidationException("Limit must be between 1 and 100")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            'search_id': self.search_id,
            'matches_only': self.matches_only
        }
        if self.limit is not None:
            data['limit'] = self.limit
        return data


@dataclass
class GetSearchResultsResponse:
    """DTO for search results response with grouped matches."""
    message: str
    search_id: str
    search_type: str
    file_path: str
    status: str
    notification_sent: bool
    total_matches: int
    unique_persons: int
    grouped_results: List[Dict[str, Any]]  # Grouped by person
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'search': {
                'id': self.search_id,
                'type': self.search_type,
                'file_path': self.file_path,
                'status': self.status,
                'notification_sent': self.notification_sent,
                'created_at': self.created_at
            },
            'results': {
                'total_matches': self.total_matches,
                'unique_persons': self.unique_persons,
                'matches': self.grouped_results
            }
        }


# ============================================================================
# NOTIFICATION DTOs
# ============================================================================

@dataclass
class SendMissingPersonNotificationRequest:
    """DTO for sending notification to missing person reporters."""
    search_id: str
    person_id: str

    def __post_init__(self):
        """Validate notification request."""
        if not self.search_id:
            raise ValidationException("Search ID is required")
        if not self.person_id:
            raise ValidationException("Person ID is required")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'search_id': self.search_id,
            'person_id': self.person_id
        }


@dataclass
class SendMissingPersonNotificationResponse:
    """DTO for notification response."""
    message: str
    search_id: str
    person_id: str
    person_name: str
    notifications_sent: int
    reporter_contacts: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'search_id': self.search_id,
            'person_id': self.person_id,
            'person_name': self.person_name,
            'notifications_sent': self.notifications_sent,
            'reporter_contacts': self.reporter_contacts
        }


# ============================================================================
# COMMON RESPONSE DTOs
# ============================================================================

@dataclass
class IdentificationDeleteResponse:
    """Delete response for identification resources."""
    message: str
    id: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'message': self.message,
            'id': self.id
        }