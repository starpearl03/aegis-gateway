from typing import TypeVar, Generic, Optional
from dataclasses import dataclass

from src.shared.response.error_detail import ErrorDetail

T = TypeVar('T')


@dataclass
class ApiResponse(Generic[T]):
    """
    Generic API response wrapper for consistent service responses.
    Contains either success data or error information, never both.
    """
    error: Optional[ErrorDetail] = None
    message: Optional[str] = None
    value: Optional[T] = None

    def __init__(self, error: Optional[ErrorDetail] = None,
                 message: Optional[str] = None,
                 value: Optional[T] = None):
        """
        Initialize API response.

        Args:
            error: Error detail object for failures
            message: Success or general message
            value: Response data for successful operations
        """
        self.error = error
        self.message = message
        self.value = value

    def is_success(self) -> bool:
        """Check if response represents a successful operation."""
        return self.error is None and self.value is not None

    def is_failure(self) -> bool:
        """Check if response represents a failed operation."""
        return self.error is not None

    def has_message(self) -> bool:
        """Check if response has a message."""
        return self.message is not None and self.message.strip() != ""

    def get_status_code(self) -> int:
        """Get HTTP status code from error or default to 200 for success."""
        if self.error:
            return self.error.status
        return 200 if self.is_success() else 400

    def to_dict(self) -> dict:
        """Convert response to dictionary format."""
        result = {}

        if self.error:
            result['error'] = self.error.to_dict()

        if self.message:
            result['message'] = self.message

        if self.value is not None:
            # If value has to_dict method, use it, otherwise include as-is
            if hasattr(self.value, 'to_dict'):
                result['value'] = self.value.to_dict()
            else:
                result['value'] = self.value

        return result

    @classmethod
    def success(cls, value: T, message: Optional[str] = None) -> 'ApiResponse[T]':
        """
        Create a successful response.

        Args:
            value: Response data
            message: Optional success message

        Returns:
            ApiResponse with success data
        """
        return cls(value=value, message=message)

    @classmethod
    def failure(cls, error: ErrorDetail, message: Optional[str] = None) -> 'ApiResponse[T]':
        """
        Create a failure response.

        Args:
            error: Error detail object
            message: Optional error message

        Returns:
            ApiResponse with error information
        """
        return cls(error=error, message=message)