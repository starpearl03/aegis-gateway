from enum import Enum


class SearchType(Enum):
    """Type of identification search"""
    CRIMINAL = "criminal"
    MISSING_PERSON = "missing_person"


class FileType(Enum):
    """Type of file uploaded for identification"""
    IMAGE = "image"
    VIDEO = "video"


class SearchStatus(Enum):
    """Status of identification search"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PersonType(Enum):
    """Type of person matched in identification"""
    CRIMINAL = "criminal"
    MISSING_PERSON = "missing_person"